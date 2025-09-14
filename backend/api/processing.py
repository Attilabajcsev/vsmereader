import os
import subprocess
import logging
from threading import Thread
from datetime import datetime, timezone
from django.conf import settings
from django.core.files import File
from django.db import transaction
from .models import Report
from .oim import extract_metadata, extract_facts
from .models import Report, Fact
import zipfile
import tempfile
import shutil

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _candidate_commands(input_path: str, output_path: str, output_dir: str) -> list[list[str]]:
    plugins = settings.ARELLE_PLUGINS
    base = [
        "python",
        "/opt/arelle/arelleCmdLine.py",
        "--file",
        input_path,
        "--validate",
        "--logLevel", "debug",
        "--logFile", os.path.join(output_dir, "arelle_cli.log"),
    ]
    # Try known flag variants across Arelle versions
    variants: list[list[str]] = []

    # Preferred: load Save Loadable OIM by absolute path, plus inlineXbrlDocumentSet by name, and save OIM JSON
    variants.append([
        "--plugins", "/opt/arelle/arelle/plugin/saveLoadableOIM.py",
        "--plugins", "inlineXbrlDocumentSet",
        "--saveLoadableOIM", output_path,
    ])

    # Alternate: names (if path variant not supported) pipe-separated, and save OIM JSON
    variants.append([
        "--plugins", "saveLoadableOIM|inlineXbrlDocumentSet",
        "--saveLoadableOIM", output_path,
    ])

    # Fallbacks (older/other spellings)
    variants.append([
        "--plugins", "Save Loadable OIM|Inline XBRL Document Set",
        "--saveLoadableOIM", output_path,
    ])
    variants.append([
        "--plugins", plugins,
        "--saveLoadableOIM", output_path,
    ])

    return [base + v for v in variants]


def _run_arelle(input_path: str, output_path: str) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["ARELLE_CACHE_DIR"] = settings.ARELLE_CACHE_DIR
    _ensure_dir(output_path)
    start_time = datetime.now(timezone.utc).timestamp()
    last_code = 1
    last_out = ""
    last_err = ""
    for cmd in _candidate_commands(input_path, output_path, os.path.dirname(output_path)):
        logger.info("Running Arelle: %s", " ".join(cmd))
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd="/opt/arelle",
        )
        last_code, last_out, last_err = proc.returncode, proc.stdout, proc.stderr
        logger.info("Arelle finished: returncode=%s", proc.returncode)
        if proc.stdout:
            logger.debug("Arelle stdout: %s", proc.stdout[:5000])
        if proc.stderr:
            logger.warning("Arelle stderr: %s", proc.stderr[:5000])
        if proc.returncode == 0 and os.path.exists(output_path):
            break
        if proc.returncode == 0:
            # Some variants write to a default file name; leave loop to post-scan
            break
    return last_code, last_out, last_err


def _run_arelle_python_api(input_path: str, output_dir: str) -> tuple[bool, str | None, str]:
    """Use Arelle's Python API to export OIM xBRL-JSON. Returns (ok, json_path, log)."""
    try:
        # API is provided by arelle-release package
        from arelle import Cntlr

        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, f"oim_{os.path.basename(input_path)}.json")
        controller = Cntlr.Cntlr(logFileName=os.path.join(output_dir, "arelle_api.log"))
        # Load model
        model_xbrl = controller.modelManager.load("file://" + os.path.abspath(input_path))
        if model_xbrl is None:
            return False, None, "model_xbrl is None"

        # NOTE: saveInstance may not be available across versions; leaving as no-op here.
        return False, None, "api-export-disabled"
    except Exception as e:
        return False, None, f"api-error: {e}"


def _is_oim_json_data(data: object) -> bool:
    if isinstance(data, dict):
        # OIM JSON commonly provides 'facts' as dict or list; accept either
        if "facts" in data and isinstance(data["facts"], (dict, list)):
            return True
        # some variants might use 'report' with 'facts'
        report = data.get("report") if isinstance(data, dict) else None
        if isinstance(report, dict) and "facts" in report:
            return True
    return False


def _is_oim_json_file(json_path: str) -> bool:
    try:
        import json as _json
        with open(json_path, "r", encoding="utf-8") as jf:
            data = _json.load(jf)
        return _is_oim_json_data(data)
    except Exception:
        return False


def _resolve_effective_input_path(original_path: str, work_base_dir: str) -> tuple[str, str | None]:
    """Return an input file path Arelle can open. If original is a .zip IXDS, unzip and pick first .xhtml."""
    lower = original_path.lower()
    if lower.endswith(".xhtml") or lower.endswith(".html"):
        return original_path, None
    if lower.endswith(".zip"):
        try:
            temp_dir = tempfile.mkdtemp(prefix="ixds_", dir=work_base_dir)
            with zipfile.ZipFile(original_path, 'r') as zf:
                zf.extractall(temp_dir)
            # find first .xhtml within extracted
            chosen: str | None = None
            for root, _dirs, files in os.walk(temp_dir):
                for name in files:
                    if name.lower().endswith((".xhtml", ".html")):
                        chosen = os.path.join(root, name)
                        break
                if chosen:
                    break
            return (chosen or original_path), temp_dir
        except Exception:
            # fallback to original_path
            return original_path, None
    return original_path, None


def _short_summary(stdout: str, stderr: str) -> str:
    if stderr.strip():
        text = stderr.strip()
    else:
        text = stdout.strip()
    if len(text) > 1000:
        return text[:1000] + "…"
    return text


def process_report_async(report_id: int) -> None:
    thread = Thread(target=_process_report_sync, args=(report_id,), daemon=True)
    thread.start()


def _process_report_sync(report_id: int) -> None:
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        logger.error("Report not found for processing: id=%s", report_id)
        return

    input_path = report.original_file.path
    output_dir = os.path.join(settings.MEDIA_ROOT, "reports", "oim")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"report_{report.id}.json")

    # Mark start time to detect newly generated files
    start_time = datetime.now(timezone.utc).timestamp()

    # For .zip IXDS, extract and select the first .xhtml to avoid encoding issues
    effective_input, temp_dir = _resolve_effective_input_path(input_path, output_dir)

    logger.info("Starting validation for report id=%s", report_id)
    code, out, err = _run_arelle(effective_input, output_path)

    generated_path = output_path if os.path.exists(output_path) else None
    if code == 0 and not generated_path:
        # Some Arelle versions ignore target name; try to locate the newest JSON in output dir
        try:
            # recursively scan output dir then input dir; choose only valid OIM JSONs
            search_dirs_priority = [output_dir, os.path.dirname(input_path)]
            generated_path = None
            for d in search_dirs_priority:
                if not os.path.isdir(d):
                    continue
                candidates: list[str] = []
                for root, _dirs, files in os.walk(d):
                    for name in files:
                        if not name.lower().endswith(".json"):
                            continue
                        p = os.path.join(root, name)
                        try:
                            os.path.getmtime(p)
                        except OSError:
                            continue
                        if _is_oim_json_file(p):
                            candidates.append(p)
                candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                if candidates:
                    generated_path = candidates[0]
                    break
            if generated_path:
                logger.info(
                    "OIM output file not at expected path; using latest JSON: %s (searched %s)",
                    generated_path,
                    search_dirs_priority,
                )
        except Exception:
            logger.exception("Failed scanning for generated OIM JSON in %s", output_dir)

    # If CLI failed to produce a usable JSON, or produced a non-OIM JSON, try Python API fallback
    if (code != 0 or not generated_path or not os.path.exists(generated_path) or not _is_oim_json_file(generated_path)):
        ok, api_json, api_log = _run_arelle_python_api(effective_input, output_dir)
        if ok and api_json:
            generated_path = api_json
            code = 0
            out = (out or "") + f"\n[api] {api_log}"
        else:
            err = (err or "") + f"\n[api] {api_log}"

    # Final guard: only accept actual OIM JSONs with facts
    if code == 0 and generated_path and os.path.exists(generated_path) and _is_oim_json_file(generated_path):
        # Save generated JSON to FileField
        with open(generated_path, "rb") as f:
            django_file = File(f)
            filename = os.path.basename(generated_path)
            # Use a transaction to avoid partial updates
            with transaction.atomic():
                report.status = Report.Status.VALIDATED
                report.validation_summary = _short_summary(out, err) or "Validated"
                report.taxonomy_version = settings.VSME_ENTRYPOINT_URL
                report.oim_json_file.save(filename, django_file, save=False)
                report.failure_reason = ""
                report.save()
        # Populate metadata best-effort and persist facts
        try:
            import json as _json
            with open(generated_path, "r", encoding="utf-8") as jf:
                oim_json = _json.load(jf)
            entity, period = extract_metadata(oim_json)
            if entity or period:
                with transaction.atomic():
                    if entity:
                        report.entity = entity
                    if period:
                        report.reporting_period = period
                    report.save(update_fields=["entity", "reporting_period", "updated_at"])
            # Save facts
            fact_rows = list(extract_facts(oim_json))
            to_create: list[Fact] = []
            for r in fact_rows:
                to_create.append(
                    Fact(
                        report=report,
                        concept=r.get("concept", ""),
                        value=r.get("value", ""),
                        datatype=r.get("datatype", ""),
                        unit=r.get("unit", ""),
                        context=r.get("context", ""),
                    )
                )
            if to_create:
                Fact.objects.bulk_create(to_create, batch_size=1000)
                logger.info("Saved %d facts for report id=%s", len(to_create), report_id)
        except Exception:
            logger.warning("Metadata extraction failed for report id=%s", report_id)
        logger.info("Report validated successfully id=%s", report_id)
    else:
        # Provide helpful debug in failure
        try:
            scans = []
            for d in [output_dir, os.path.dirname(input_path)]:
                if os.path.isdir(d):
                    for root, _dirs, files in os.walk(d):
                        for name in files:
                            if name.lower().endswith('.json'):
                                scans.append(os.path.join(root, name))
            if scans:
                logger.info("Found JSON files during scan: %s", scans[:20])
        except Exception:
            pass
        with transaction.atomic():
            report.status = Report.Status.FAILED
            failure = _short_summary(out, err)
            if not failure:
                failure = "Validation produced no OIM facts JSON. Ensure Save Loadable OIM plugin is active."
            report.failure_reason = failure
            report.validation_summary = ""
            report.save()
        logger.error(
            "Report validation failed id=%s (code=%s, expected_output=%s, exists=%s)",
            report_id,
            code,
            output_path,
            os.path.exists(output_path),
        )

    # Cleanup temp extracted directory if any
    try:
        if 'temp_dir' in locals() and temp_dir and os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        logger.warning("Failed to cleanup temp IXDS dir %s", temp_dir)


