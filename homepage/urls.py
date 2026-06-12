from django.urls import path
from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('dashboard/department-chart/', views.DepartmentChartView.as_view(), name='department_chart'),
    path('memberships/<pk>/grant-role/', views.GrantRoleView.as_view(), name='grant_role'),
    path('memberships/<pk>/revoke-role/', views.RevokeRoleView.as_view(), name='revoke_role'),
    path('memberships/<pk>/change-department/', views.ChangeDepartmentView.as_view(), name='change_department'),
]
