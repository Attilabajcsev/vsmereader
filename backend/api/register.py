from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Tuple
from django.db import transaction
from .models import Report, Fact, VsmeRegister
import logging


def _to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        # Replace commas as thousand separators if present
        s = s.replace(",", "")
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _first_fact(report: Report, fragments: Iterable[str]) -> Fact | None:
    for frag in fragments:
        f = (
            Fact.objects.filter(report=report, concept__icontains=frag)
            .order_by("id")
            .first()
        )
        if f:
            return f
    return None


def _collect_metrics(report: Report) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return (values, sources) for register metrics.

    values: dict of {field_name: value or unit string}
    sources: dict of {code: {concept, unit}}
    """

    mapping = {
        # code: (value_field, unit_field, [concept fragments])
        "employees": ("employees_value", "employees_unit", ["NumberOfEmployees", "Employees"]),
        "ghg_total": ("ghg_total_value", "ghg_total_unit", ["TotalGHG", "GHGEmissions", "GreenhouseGasEmissions"]),
        "ghg_scope1": ("ghg_scope1_value", "ghg_scope1_unit", ["Scope1", "GHGScope1"]) ,
        "ghg_scope2": ("ghg_scope2_value", "ghg_scope2_unit", ["Scope2", "GHGScope2"]) ,
        "energy_consumption": ("energy_consumption_value", "energy_consumption_unit", ["TotalEnergyConsumption", "EnergyConsumption"]) ,
        "renewable_energy_share": ("renewable_energy_share_value", "renewable_energy_share_unit", ["RenewableEnergyShare", "ShareOfRenewable"]) ,
        "water_withdrawal": ("water_withdrawal_value", "water_withdrawal_unit", ["WaterWithdrawal"]) ,
        "water_discharge": ("water_discharge_value", "water_discharge_unit", ["WaterDischarge"]) ,
        "waste_generated": ("waste_generated_value", "waste_generated_unit", ["WasteGenerated", "TotalWasteGenerated"]) ,
        "hazardous_waste": ("hazardous_waste_value", "hazardous_waste_unit", ["HazardousWaste"]) ,
        "non_hazardous_waste": ("non_hazardous_waste_value", "non_hazardous_waste_unit", ["NonHazardousWaste"]) ,
    }

    values: Dict[str, Any] = {}
    sources: Dict[str, Any] = {}

    for code, (v_field, u_field, frags) in mapping.items():
        fact = _first_fact(report, frags)
        if fact:
            dec = _to_decimal(fact.value)
            if dec is not None:
                values[v_field] = dec
            if fact.unit:
                values[u_field] = fact.unit
            sources[code] = {"concept": fact.concept, "unit": fact.unit}
        else:
            # ensure absent metrics don't overwrite existing values unintentionally in upsert
            pass

    return values, sources


def _compute_completeness(values: Dict[str, Any]) -> int:
    target_value_fields = [
        "employees_value",
        "ghg_total_value",
        "ghg_scope1_value",
        "ghg_scope2_value",
        "energy_consumption_value",
        "renewable_energy_share_value",
        "water_withdrawal_value",
        "water_discharge_value",
        "waste_generated_value",
        "hazardous_waste_value",
        "non_hazardous_waste_value",
    ]
    present = sum(1 for k in target_value_fields if k in values and values[k] is not None)
    total = len(target_value_fields)
    if total == 0:
        return 0
    pct = int((present / total) * 100)
    return max(0, min(100, pct))


def upsert_vsme_register(report: Report) -> VsmeRegister:
    """Upsert VsmeRegister row for the report's company-year based on its facts."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Ensure we only process validated reports
    if report.status != Report.Status.VALIDATED:
        return None  # type: ignore

    values, sources = _collect_metrics(report)
    # Always refresh entity_identifier from report
    entity_identifier = report.entity or ""
    completeness = _compute_completeness(values)
    
    # Log what we extracted for debugging
    fact_count = report.facts.count()
    logger.info("VsmeRegister update for report %s: extracted %d facts, %d metric values, completeness=%d%%", 
                report.id, fact_count, len(values), completeness)

    with transaction.atomic():
        row, created = VsmeRegister.objects.select_for_update().get_or_create(
            company=report.company,
            year=report.reporting_year,
            defaults={
                "entity_identifier": entity_identifier,
                "completeness_score": completeness,
                "last_report": report,
                "source_concepts": sources,
            }
        )
        if not created:
            # Clear all metric fields first to avoid contamination from previous reports
            metric_fields = [
                "employees_value", "employees_unit",
                "ghg_total_value", "ghg_total_unit",
                "ghg_scope1_value", "ghg_scope1_unit",
                "ghg_scope2_value", "ghg_scope2_unit",
                "energy_consumption_value", "energy_consumption_unit",
                "renewable_energy_share_value", "renewable_energy_share_unit",
                "water_withdrawal_value", "water_withdrawal_unit",
                "water_discharge_value", "water_discharge_unit",
                "waste_generated_value", "waste_generated_unit",
                "hazardous_waste_value", "hazardous_waste_unit",
                "non_hazardous_waste_value", "non_hazardous_waste_unit",
            ]
            
            # Clear all metric fields to prevent contamination
            for field in metric_fields:
                setattr(row, field, None)
            
            # Now set new values from current report
            for field, val in values.items():
                setattr(row, field, val)
            
            row.entity_identifier = entity_identifier or row.entity_identifier
            row.completeness_score = completeness
            row.last_report = report
            # Replace sources completely (don't merge with old data)
            row.source_concepts = sources
            row.save()
        else:
            # For a new row, set metric fields
            for field, val in values.items():
                setattr(row, field, val)
            row.save()
    return row


def recompute_vsme_register(company_id: int, year: int) -> None:
    """Recompute or remove VsmeRegister for a company-year after report deletion.

    - If there is any remaining VALIDATED report for the same company-year, upsert from the latest one.
    - If none remain, delete the VsmeRegister row if present.
    """
    try:
        latest = (
            Report.objects.filter(
                company_id=company_id,
                reporting_year=year,
                status=Report.Status.VALIDATED,
            )
            .order_by("-created_at")
            .first()
        )
        if latest:
            upsert_vsme_register(latest)
        else:
            row = VsmeRegister.objects.filter(company_id=company_id, year=year).first()
            if row:
                row.delete()
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed to recompute VsmeRegister for company=%s year=%s", company_id, year
        )


def rebuild_all_vsme_registers() -> dict:
    """Rebuild the entire VsmeRegister table from current VALIDATED reports.

    - Upserts rows for each (company, year) that has at least one VALIDATED report
    - Deletes VsmeRegister rows that no longer have any corresponding reports
    Returns a summary dict of actions.
    """
    summary = {"upserted": 0, "deleted": 0}
    try:
        # Compute desired set from reports
        desired_pairs = set(
            Report.objects.filter(status=Report.Status.VALIDATED)
            .values_list("company_id", "reporting_year")
            .distinct()
        )
        # Upsert for each desired pair using latest report
        for (company_id, year) in desired_pairs:
            latest = (
                Report.objects.filter(
                    company_id=company_id,
                    reporting_year=year,
                    status=Report.Status.VALIDATED,
                )
                .order_by("-created_at")
                .first()
            )
            if latest:
                upsert_vsme_register(latest)
                summary["upserted"] += 1

        # Delete rows that are not in desired set
        existing_pairs = set(
            VsmeRegister.objects.values_list("company_id", "year")
        )
        to_delete = existing_pairs - desired_pairs
        if to_delete:
            for (company_id, year) in to_delete:
                VsmeRegister.objects.filter(company_id=company_id, year=year).delete()
                summary["deleted"] += 1
    except Exception:
        logging.getLogger(__name__).exception("Failed full rebuild of VsmeRegister")
    return summary

