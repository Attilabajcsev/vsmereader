from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Report, VsmeRegister
from .register import recompute_vsme_register
import logging

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Report)
def cleanup_vsme_register_on_report_delete(sender, instance, **kwargs):
    """
    Clean up VsmeRegister entries when a Report is deleted.
    This handles both direct report deletion and cascade deletion from user deletion.
    """
    try:
        recompute_vsme_register(instance.company_id, instance.reporting_year)
        logger.info(
            f"Cleaned up VsmeRegister for company_id={instance.company_id}, year={instance.reporting_year} after report deletion"
        )
    except Exception as e:
        logger.error(
            f"Failed to cleanup VsmeRegister for company_id={instance.company_id}, year={instance.reporting_year}: {e}"
        )


@receiver(post_delete, sender=Report)
def renumber_user_reports_on_delete(sender, instance, **kwargs):
    """
    Renumber remaining reports for the user to maintain sequential numbering.
    """
    try:
        # Get all remaining reports for this user, ordered by creation time
        remaining_reports = Report.objects.filter(owner=instance.owner).order_by('created_at')
        
        # Renumber them sequentially
        for i, report in enumerate(remaining_reports, 1):
            if report.user_report_number != i:
                report.user_report_number = i
                report.save(update_fields=['user_report_number'])
        
        logger.info(f"Renumbered {remaining_reports.count()} reports for user {instance.owner.username}")
    except Exception as e:
        logger.error(f"Failed to renumber reports for user {instance.owner.username}: {e}")


@receiver(pre_delete, sender=User)
def cleanup_vsme_register_on_user_delete(sender, instance, **kwargs):
    """
    Clean up VsmeRegister entries when a User is deleted.
    This collects all (company_id, year) pairs from the user's reports before they are cascade deleted.
    """
    try:
        # Collect all (company_id, year) pairs from user's validated reports before cascade deletion
        company_year_pairs = list(
            Report.objects.filter(
                owner=instance, 
                status=Report.Status.VALIDATED
            ).values_list('company_id', 'reporting_year').distinct()
        )
        
        # Store them for post-delete cleanup
        if company_year_pairs:
            # Use a custom attribute to pass data to post_delete signal
            instance._vsme_cleanup_pairs = company_year_pairs
            logger.info(
                f"Marked {len(company_year_pairs)} company-year pairs for VsmeRegister cleanup after user deletion"
            )
    except Exception as e:
        logger.error(f"Failed to prepare VsmeRegister cleanup for user deletion: {e}")


@receiver(post_delete, sender=User)
def execute_vsme_register_cleanup_on_user_delete(sender, instance, **kwargs):
    """
    Execute the VsmeRegister cleanup after user and their reports are deleted.
    """
    try:
        # Get the pairs we stored in pre_delete
        company_year_pairs = getattr(instance, '_vsme_cleanup_pairs', [])
        
        for company_id, year in company_year_pairs:
            recompute_vsme_register(company_id, year)
            logger.info(
                f"Cleaned up VsmeRegister for company_id={company_id}, year={year} after user deletion"
            )
    except Exception as e:
        logger.error(f"Failed to execute VsmeRegister cleanup after user deletion: {e}")
