from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Report, Company, VsmeRegister
from django.conf import settings


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class OAuthUserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer only used for Google OAuth logins. Same as UserSerializer but we don't expect password from user. We use unusable password instead.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        return user


class ReportListSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "company",
            "reporting_year",
            "entity",
            "reporting_period",
            "status",
            "created_at",
        ]

    def get_company(self, obj: Report) -> dict | None:
        if not obj.company_id:
            return None
        return {"id": obj.company_id, "name": obj.company.name}


class ReportDetailSerializer(serializers.ModelSerializer):
    original_file_url = serializers.SerializerMethodField()
    oim_json_file_url = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "company",
            "reporting_year",
            "entity",
            "reporting_period",
            "taxonomy_version",
            "status",
            "validation_summary",
            "failure_reason",
            "original_file_url",
            "oim_json_file_url",
            "created_at",
            "updated_at",
        ]

    def get_original_file_url(self, obj: Report) -> str | None:
        return obj.original_file.url if obj.original_file else None

    def get_oim_json_file_url(self, obj: Report) -> str | None:
        return obj.oim_json_file.url if obj.oim_json_file else None

    def get_company(self, obj: Report) -> dict | None:
        if not obj.company_id:
            return None
        return {"id": obj.company_id, "name": obj.company.name}


class ReportUploadSerializer(serializers.Serializer):
    # Use Serializer instead of ModelSerializer for full control
    original_file = serializers.FileField()
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False, allow_null=True)
    reporting_year = serializers.IntegerField(required=False, allow_null=True)
    company_name = serializers.CharField(required=False, allow_blank=True)

    def validate_original_file(self, file):
        name = (file.name or "").lower()
        if not (name.endswith(".xhtml") or name.endswith(".html") or name.endswith(".zip")):
            raise serializers.ValidationError("Accepted file types: .xhtml, .html, or .zip (IXDS)")

        from django.conf import settings
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size and file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        return file

    def validate_reporting_year(self, year):
        if year is None:
            return year  # Allow None, will be auto-extracted
        try:
            y = int(year)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Invalid year")
        if y < 1900 or y > 2100:
            raise serializers.ValidationError("Year must be between 1900 and 2100")
        return y

    def validate(self, attrs):
        # Optional per-user quota enforcement
        from django.contrib.auth.models import AnonymousUser
        from django.conf import settings as dj_settings
        user = getattr(self.context.get("request"), "user", None)
        max_reports = getattr(dj_settings, "MAX_REPORTS_PER_USER", 0)
        if max_reports and user and not isinstance(user, AnonymousUser):
            count = Report.objects.filter(owner=user).count()
            if count >= max_reports:
                raise serializers.ValidationError({
                    "non_field_errors": [f"Report quota exceeded. Max {max_reports} reports per user."],
                })
        
        return attrs

    def create(self, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        user = self.context["request"].user
        original_file = validated_data["original_file"]
        
        # Get provided values
        company = validated_data.get("company")
        reporting_year = validated_data.get("reporting_year")
        company_name = validated_data.get("company_name", "").strip()
        
        logger.info("Creating report with data: company=%s, year=%s, company_name='%s'", company, reporting_year, company_name)
        
        # Create a fallback company if none provided
        if not company and not company_name:
            # Extract filename as company name fallback
            filename = original_file.name
            if filename:
                # Use filename without extension as company name
                company_name = filename.rsplit('.', 1)[0]
                logger.info("Using filename as company fallback: '%s'", company_name)
        
        # Handle company creation/lookup
        if not company:
            if company_name:
                # Try to find existing company by name (case-insensitive)
                company = Company.objects.filter(name__iexact=company_name).first()
                if not company:
                    # Create new company
                    company = Company.objects.create(name=company_name)
                    logger.info("Created new company: %s", company.name)
            else:
                # Last resort: create a generic company
                company_name = "Unknown Company"
                company = Company.objects.filter(name__iexact=company_name).first()
                if not company:
                    company = Company.objects.create(name=company_name)
                logger.info("Created fallback company: %s", company.name)
        
        # Use default year if none provided (will be updated during processing)
        if not reporting_year:
            reporting_year = 2024  # Default fallback year
            logger.info("Using default reporting year: %s", reporting_year)
        
        # Check for duplicates with a unique suffix if needed
        base_company = company
        counter = 1
        while Report.objects.filter(company=company, reporting_year=reporting_year).exists():
            # Create a variant company name to avoid duplicates
            variant_name = f"{base_company.name} ({counter})"
            company = Company.objects.filter(name__iexact=variant_name).first()
            if not company:
                company = Company.objects.create(name=variant_name)
            counter += 1
            if counter > 10:  # Prevent infinite loop
                break
        
        logger.info("Creating report for company=%s, year=%s", company.name, reporting_year)
        
        return Report.objects.create(
            owner=user,
            original_file=original_file,
            company=company,
            reporting_year=reporting_year
        )

    def validate_original_file(self, file):
        name = (file.name or "").lower()
        if not (name.endswith(".xhtml") or name.endswith(".html") or name.endswith(".zip")):
            raise serializers.ValidationError("Accepted file types: .xhtml, .html, or .zip (IXDS)")

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size and file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        return file

    def validate_reporting_year(self, year):
        if year is None:
            return year  # Allow None, will be auto-extracted
        try:
            y = int(year)
        except (TypeError, ValueError):
            raise serializers.ValidationError("Invalid year")
        if y < 1900 or y > 2100:
            raise serializers.ValidationError("Year must be between 1900 and 2100")
        return y

    def validate(self, attrs):
        attrs = super().validate(attrs)
        
        # Optional per-user quota enforcement
        from django.contrib.auth.models import AnonymousUser
        from django.conf import settings as dj_settings
        user = getattr(self.context.get("request"), "user", None)
        max_reports = getattr(dj_settings, "MAX_REPORTS_PER_USER", 0)
        if max_reports and user and not isinstance(user, AnonymousUser):
            count = Report.objects.filter(owner=user).count()
            if count >= max_reports:
                raise serializers.ValidationError({
                    "non_field_errors": [f"Report quota exceeded. Max {max_reports} reports per user."],
                })
        
        return attrs


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]


class VsmeRegisterListSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    class Meta:
        model = VsmeRegister
        fields = [
            "id",
            "company",
            "year",
            "entity_identifier",
            "employees_value",
            "ghg_total_value",
            "energy_consumption_value",
            "water_withdrawal_value",
            "waste_generated_value",
            "completeness_score",
            "updated_at",
        ]

    def get_company(self, obj: VsmeRegister) -> dict:
        return {"id": obj.company_id, "name": obj.company.name}


class VsmeRegisterDetailSerializer(serializers.ModelSerializer):
    company = serializers.SerializerMethodField()

    class Meta:
        model = VsmeRegister
        fields = "__all__"

    def get_company(self, obj: VsmeRegister) -> dict:
        return {"id": obj.company_id, "name": obj.company.name}
