from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Report
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
    class Meta:
        model = Report
        fields = [
            "id",
            "entity",
            "reporting_period",
            "status",
            "created_at",
        ]


class ReportDetailSerializer(serializers.ModelSerializer):
    original_file_url = serializers.SerializerMethodField()
    oim_json_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
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


class ReportUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["id", "original_file"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Report.objects.create(owner=user, **validated_data)

    def validate_original_file(self, file):
        name = (file.name or "").lower()
        if not (name.endswith(".xhtml") or name.endswith(".zip")):
            raise serializers.ValidationError("Accepted file types: .xhtml or .zip (IXDS)")

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file.size and file.size > max_bytes:
            raise serializers.ValidationError(
                f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        return file
