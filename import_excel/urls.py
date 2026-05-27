from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("import/", views.import_center, name="import_center"),
    path("personnel/", views.personnel_presence_list, name="personnel_presence_list"),
    path("personnel/<int:pk>/edit/", views.personnel_presence_edit, name="personnel_presence_edit"),
    path("reports/pc/", views.report_pc, name="report_pc"),
    path("reports/abs/", views.report_abs, name="report_abs"),
    path("reports/abs-se-without-ki/", views.report_abs_se_without_ki, name="report_abs_se_without_ki"),
    path("reports/to/", views.report_to, name="report_to"),
    path("reports/abs-comp/", views.report_abs_comp, name="report_abs_comp"),
    path("reports/actual-vs-budget/", views.report_actual_vs_budget, name="report_actual_vs_budget"),
    path("reports/analytics/", views.analytics, name="analytics"),
    path("api/import/upload/", views.api_import_upload, name="api_import_upload"),
    path("api/import/preview/", views.api_import_preview, name="api_import_preview"),
    path("api/import/headers/", views.api_import_headers, name="api_import_headers"),
    path("api/import/status/<int:import_id>/", views.api_import_status, name="api_import_status"),
    path("api/import/data/<int:import_id>/", views.api_import_data, name="api_import_data"),
    path("api/import/delete-period/", views.api_delete_period, name="api_delete_period"),
    path("api/import/clear-log/", views.api_clear_import_log, name="api_clear_import_log"),
    path("api/budget/save/", views.api_save_budget, name="api_save_budget"),
]
