import os
import subprocess
import logging
from threading import Thread
from datetime import datetime, timezone
from django.conf import settings
from django.core.files import File
from django.db import transaction
from .models import Report
from .oim import extract_metadata

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
    ]
    # Try known flag variants across Arelle versions
    variants: list[list[str]] = []

    # Preferred: separate --plugins flags
    variants.append([
        "--plugins", "saveLoadableOIM",
        "--plugins", "inlineXbrlDocumentSet",
        "--saveOIMinstance", output_dir,
    ])

    # Alternate: pipe-separated plugin list
    variants.append([
        "--plugins", "saveLoadableOIM|inlineXbrlDocumentSet",
        "--saveOIMinstance", output_dir,
    ])

    # Fallbacks (older/other spellings)
    variants.append([
        "--plugins", "Save Loadable OIM|Inline XBRL Document Set",
        "--saveOIMinstance", output_dir,
    ])
    variants.append([
        "--plugins", plugins,
        "--saveOIMinstance", output_dir,
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

        # Save as OIM JSON
        controller.modelManager.saveInstance(json_path, outputType="XBRL-JSON")

        if os.path.exists(json_path):
            return True, json_path, "api-export-ok"
        return False, None, "json not created"
    except Exception as e:
        return False, None, f"api-error: {e}"


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

    logger.info("Starting validation for report id=%s", report_id)
    code, out, err = _run_arelle(input_path, output_path)

    generated_path = output_path if os.path.exists(output_path) else None
    if code == 0 and not generated_path:
        # Some Arelle versions ignore target name; try to locate the newest JSON in output dir
        try:
            # recursively scan output dir then input dir; avoid scanning /opt/arelle tests
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

    # If CLI failed to produce a usable JSON, try Python API fallback
    if (code != 0 or not generated_path or not os.path.exists(generated_path)):
        ok, api_json, api_log = _run_arelle_python_api(input_path, output_dir)
        if ok and api_json:
            generated_path = api_json
            code = 0
            out = (out or "") + f"\n[api] {api_log}"
        else:
            err = (err or "") + f"\n[api] {api_log}"

    if code == 0 and generated_path and os.path.exists(generated_path):
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
        # Populate metadata best-effort
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
        except Exception:
            logger.warning("Metadata extraction failed for report id=%s", report_id)
        logger.info("Report validated successfully id=%s", report_id)
    else:
        with transaction.atomic():
            report.status = Report.Status.FAILED
            report.failure_reason = _short_summary(out, err) or "Validation failed"
            report.validation_summary = ""
            report.save()
        logger.error(
            "Report validation failed id=%s (code=%s, expected_output=%s, exists=%s)",
            report_id,
            code,
            output_path,
            os.path.exists(output_path),
        )


