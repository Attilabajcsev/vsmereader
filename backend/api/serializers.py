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


class ReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "original_file", "company", "reporting_year"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Report.objects.create(owner=user, **validated_data)

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

    def validate_reporting_year(self, year: int) -> int:
        try:
            y = int(year)
        except Exception:
            raise serializers.ValidationError("Invalid year")
        if y < 1900 or y > 2100:
            raise serializers.ValidationError("Year must be between 1900 and 2100")
        return y

    def validate(self, attrs):
        attrs = super().validate(attrs)
        company = attrs.get("company")
        year = attrs.get("reporting_year")
        if not company:
            raise serializers.ValidationError({"company": "Company is required"})
        if not year:
            raise serializers.ValidationError({"reporting_year": "Reporting year is required"})
        # Enforce uniqueness per company-year
        exists = Report.objects.filter(company=company, reporting_year=year).exists()
        if exists:
            raise serializers.ValidationError({
                "non_field_errors": ["A report for this company and year already exists."],
                "company": ["Duplicate for selected year"],
                "reporting_year": ["Duplicate for selected company"],
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
