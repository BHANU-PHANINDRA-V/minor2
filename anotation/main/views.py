import csv
import json
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import BoundingBox, Project, ProjectClass, ProjectImage


def _project_for_user(user, project_id):
    # Find one project that belongs to the logged-in user.
    return get_object_or_404(
        Project.objects.prefetch_related("classes", "images__boxes__project_class"),
        id=project_id,
        owner=user,
    )


def _project_payload(project):
    # Convert project data into a simple dictionary for JavaScript.
    return {
        "id": project.id,
        "title": project.title,
        "classes": [
            {
                "id": item.id,
                "name": item.name,
                "class_index": item.class_index,
            }
            for item in project.classes.all()
        ],
        "images": [
            {
                "id": image.id,
                "name": image.original_name,
                "url": image.image.url if image.image else "",
                "object_count": image.boxes.count(),
                "boxes": [
                    {
                        "id": box.id,
                        "box_name": box.box_name,
                        "class_id": box.project_class_id,
                        "class_name": box.project_class.name,
                        "class_index": box.project_class.class_index,
                        "object_index": box.object_index,
                        "x_min": box.x_min,
                        "y_min": box.y_min,
                        "width": box.width,
                        "height": box.height,
                    }
                    for box in image.boxes.all()
                ],
            }
            for image in project.images.all()
        ],
    }


def home(request):
    # If user is already logged in, go to dashboard.
    # Otherwise send user to login page.
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def signup_view(request):
    # Show signup page and create a new user on POST.
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        full_name = request.POST.get("full_name", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not password:
            messages.error(request, "Username and password are required.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=full_name,
            )
            login(request, user)
            return redirect("dashboard")

    return render(request, "signup.html")


def login_view(request):
    # Show login page and authenticate user on POST.
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Invalid username or password.")
        else:
            login(request, user)
            return redirect("dashboard")

    return render(request, "login.html")


@login_required
def logout_view(request):
    # Log out current user and return to login page.
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    # Show all projects created by the current user.
    projects = (
        Project.objects.filter(owner=request.user)
        .prefetch_related("classes", "images")
        .order_by("-created_at")
    )
    return render(request, "project.html", {"projects": projects})


@login_required
@transaction.atomic
def new_project_view(request):
    # Show create-project page and save a project with its class list on POST.
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        raw_classes = request.POST.get("classes", "")
        class_names = []

        for raw_item in raw_classes.replace("\r", "\n").replace(",", "\n").split("\n"):
            item = raw_item.strip()
            if item and item.lower() not in {name.lower() for name in class_names}:
                class_names.append(item)

        if not title:
            messages.error(request, "Project title is required.")
        elif not class_names:
            messages.error(request, "Add at least one class.")
        else:
            project = Project.objects.create(owner=request.user, title=title)
            ProjectClass.objects.bulk_create(
                [
                    ProjectClass(project=project, name=name, class_index=index)
                    for index, name in enumerate(class_names)
                ]
            )
            return redirect("annotation", project_id=project.id)

    return render(request, "new_project.html")


@login_required
def annotation_view(request, project_id):
    # Open annotation page for one project.
    project = _project_for_user(request.user, project_id)
    project_payload = _project_payload(project)
    return render(
        request,
        "annotation.html",
        {
            "project": project,
            "project_json": project_payload,
        },
    )


@login_required
@require_POST
def upload_images_view(request, project_id):
    # Upload one or more images for a project.
    project = _project_for_user(request.user, project_id)
    files = request.FILES.getlist("images")
    if not files:
        return JsonResponse({"error": "No images were uploaded."}, status=400)

    created_images = []
    allowed_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
    for image_file in files:
        content_type = getattr(image_file, "content_type", "") or ""
        suffix = Path(image_file.name).suffix.lower()
        if content_type and not content_type.startswith("image/"):
            if suffix not in allowed_suffixes:
                continue
        elif suffix not in allowed_suffixes:
            continue

        original_name = image_file.name.split("/")[-1]
        project_image, created = ProjectImage.objects.get_or_create(
            project=project,
            original_name=original_name,
            defaults={"image": image_file},
        )
        if not created:
            project_image.image = image_file
            project_image.save(update_fields=["image"])

        created_images.append(
            {
                "id": project_image.id,
                "name": project_image.original_name,
                "url": project_image.image.url,
                "object_count": project_image.boxes.count(),
                "boxes": [],
            }
        )

    return JsonResponse({"images": created_images})


@login_required
@require_POST
@transaction.atomic
def save_annotations_view(request, project_id, image_id):
    # Save all boxes for one image.
    project = _project_for_user(request.user, project_id)
    image = get_object_or_404(ProjectImage, id=image_id, project=project)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        boxes = payload.get("boxes", [])
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid annotation payload."}, status=400)

    image.boxes.all().delete()
    new_boxes = []

    for index, box in enumerate(boxes, start=1):
        class_id = box.get("class_id")
        project_class = get_object_or_404(ProjectClass, id=class_id, project=project)
        new_boxes.append(
            BoundingBox(
                image=image,
                project_class=project_class,
                box_name=box.get("box_name", project_class.name).strip() or project_class.name,
                object_index=index,
                x_min=float(box.get("x_min", 0)),
                y_min=float(box.get("y_min", 0)),
                width=float(box.get("width", 0)),
                height=float(box.get("height", 0)),
            )
        )

    BoundingBox.objects.bulk_create(new_boxes)

    return JsonResponse(
        {
            "message": "Annotations saved.",
            "object_count": len(new_boxes),
        }
    )


@login_required
@require_GET
def export_annotations_csv_view(request, project_id):
    # Download annotations.csv for a project.
    project = _project_for_user(request.user, project_id)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.title.lower().replace(" ", "_")}_annotations.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "file_name",
            "object_count_in_box",
            "x_min",
            "y_min",
            "width",
            "height",
            "class_id",
        ]
    )

    images = project.images.prefetch_related("boxes__project_class").all()
    for image in images:
        total_objects_in_image = image.boxes.count()
        for box in image.boxes.all():
            writer.writerow(
                [
                    image.original_name,
                    total_objects_in_image,
                    box.x_min,
                    box.y_min,
                    box.width,
                    box.height,
                    box.project_class.class_index,
                ]
            )

    return response


@login_required
@require_GET
def export_classes_view(request, project_id):
    # Download classes.txt using only classes that were actually used.
    project = _project_for_user(request.user, project_id)
    response = HttpResponse(content_type="text/plain")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.title.lower().replace(" ", "_")}_classes.txt"'
    )

    used_class_ids = (
        BoundingBox.objects.filter(image__project=project)
        .values_list("project_class_id", flat=True)
        .distinct()
    )
    used_classes = project.classes.filter(id__in=used_class_ids).order_by("class_index")

    for project_class in used_classes:
        response.write(f"{project_class.class_index} {project_class.name}\n")

    return response


@login_required
@require_GET
def project_data_view(request, project_id):
    # Send project data as JSON for the annotation page JavaScript.
    project = _project_for_user(request.user, project_id)
    return JsonResponse(_project_payload(project))
