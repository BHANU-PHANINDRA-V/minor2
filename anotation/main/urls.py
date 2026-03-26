from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("projects/new/", views.new_project_view, name="new_project"),
    path("projects/<int:project_id>/annotate/", views.annotation_view, name="annotation"),
    path("projects/<int:project_id>/data/", views.project_data_view, name="project_data"),
    path("projects/<int:project_id>/upload/", views.upload_images_view, name="upload_images"),
    path(
        "projects/<int:project_id>/images/<int:image_id>/save/",
        views.save_annotations_view,
        name="save_annotations",
    ),
    path(
        "projects/<int:project_id>/export/annotations/",
        views.export_annotations_csv_view,
        name="export_annotations_csv",
    ),
    path(
        "projects/<int:project_id>/export/classes/",
        views.export_classes_view,
        name="export_classes",
    ),
]
