from django.urls import path
from .views import (
    UserListView,
    UserRegisterView,
    UserLoginView,
    UserProfileView,
    VerificationRequestView,
    UserStatusView,
    UserPostsView,
    PostListCreateView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserApproveView,
    AdminUserRoleUpdateView,
    AdminVerificationRequestListView,
    AdminPostListView,
    AdminPostDetailView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)

app_name = 'users'

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('verification/', VerificationRequestView.as_view(), name='verification-request'),
    path('status/', UserStatusView.as_view(), name='user-status'),
    path('posts/', UserPostsView.as_view(), name='user-posts'),
    path('posts/create/', PostListCreateView.as_view(), name='post-list-create'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/<uuid:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<uuid:pk>/approve/', AdminUserApproveView.as_view(), name='admin-user-approve'),
    path('admin/users/<uuid:pk>/role/', AdminUserRoleUpdateView.as_view(), name='admin-user-role-update'),
    path('admin/verification-requests/', AdminVerificationRequestListView.as_view(), name='admin-verification-request-list'),
    path('admin/posts/', AdminPostListView.as_view(), name='admin-post-list'),
    path('admin/posts/<uuid:pk>/', AdminPostDetailView.as_view(), name='admin-post-detail'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]