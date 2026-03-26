from django.conf import settings
from django.db import models


class Project(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("owner", "title")

    def __str__(self) -> str:
        return self.title


class ProjectClass(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="classes",
    )
    name = models.CharField(max_length=120)
    class_index = models.PositiveIntegerField()

    class Meta:
        ordering = ["class_index"]
        unique_together = (
            ("project", "name"),
            ("project", "class_index"),
        )

    def __str__(self) -> str:
        return f"{self.project.title}: {self.name}"


class ProjectImage(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.FileField(upload_to="project_images/")
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("project", "original_name")

    def __str__(self) -> str:
        return self.original_name

    @property
    def count_objects(self) -> int:
        return self.boxes.count()


class BoundingBox(models.Model):
    image = models.ForeignKey(
        ProjectImage,
        on_delete=models.CASCADE,
        related_name="boxes",
    )
    project_class = models.ForeignKey(
        ProjectClass,
        on_delete=models.CASCADE,
        related_name="boxes",
    )
    box_name = models.CharField(max_length=120, blank=True)
    object_index = models.PositiveIntegerField(default=1)
    x_min = models.FloatField()
    y_min = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["object_index", "id"]

    def __str__(self) -> str:
        return f"{self.image.original_name} - {self.project_class.name}"
