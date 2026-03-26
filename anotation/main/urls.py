from django.urls import path

from . import views


urlpatterns = [
    # Start page
    path("", views.home, name="home"),

    # Authentication pages
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard page
    path("dashboard/", views.dashboard_view, name="dashboard"),

    # Project creation page
    path("projects/new/", views.new_project_view, name="new_project"),

    # Annotation page for one project
    path("projects/<int:project_id>/annotate/", views.annotation_view, name="annotation"),

    # API to get all project data in JSON
    path("projects/<int:project_id>/data/", views.project_data_view, name="project_data"),

    # API to upload images for one project
    path("projects/<int:project_id>/upload/", views.upload_images_view, name="upload_images"),

    # API to save boxes for one image
    path(
        "projects/<int:project_id>/images/<int:image_id>/save/",
        views.save_annotations_view,
        name="save_annotations",
    ),

    # Download annotations.csv
    path(
        "projects/<int:project_id>/export/annotations/",
        views.export_annotations_csv_view,
        name="export_annotations_csv",
    ),

    # Download classes.txt
    path(
        "projects/<int:project_id>/export/classes/",
        views.export_classes_view,
        name="export_classes",
    ),
]
