from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt



@require_POST
@csrf_exempt
def register_view(request):

    username = request.POST.get("username")
    password = request.POST.get("password")
    email = request.POST.get("email", "")

    if not username or not password:
        return JsonResponse(
            {
                "success": False,
                "message": "Username and password are required."
            },
            status=400
        )

    if User.objects.filter(username=username).exists():
        return JsonResponse(
            {
                "success": False,
                "message": "Username already exists."
            },
            status=400
        )

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    return JsonResponse(
        {
            "success": True,
            "message": "User registered successfully.",
            "user_id": user.id,
            "username": user.username,
        },
        status=201
    )

@csrf_exempt
@require_POST
def login_view(request):

    username = request.POST.get("username")
    password = request.POST.get("password")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid username or password."
            },
            status=401
        )

    if not user.is_active:
        return JsonResponse(
            {
                "success": False,
                "message": "This account is inactive."
            },
            status=403
        )

    login(request, user)

    return JsonResponse(
        {
            "success": True,
            "message": "Login successful.",
            "user_id": user.id,
            "username": user.username,
        }
    )

@csrf_exempt
@require_POST
def logout_view(request):

    logout(request)

    return JsonResponse(
        {
            "success": True,
            "message": "Logout successful."
        }
    )
    
def profile_view(request):

    if not request.user.is_authenticated:
        return JsonResponse(
            {
                "success": False,
                "message": "Authentication required."
            },
            status=401
        )

    user = request.user

    return JsonResponse(
        {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }
    )