from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.forms import *
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
import uuid
from .models import Listing, User, ListingResponse, ListingAvailability
from .forms import RegisterForm, ProfileCreationForm, ProfileEditForm
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import random
import json

def home(request):
    listings = Listing.objects.all()
    programming_listings = Listing.objects.filter(category='TECH')
    writing_listings = Listing.objects.filter(category='WRITING')
    business_listings = Listing.objects.filter(category='BUSINESS')
    digitalm_listings = Listing.objects.filter(category='MARKETING')

    context = {
        "listings": listings,
        'programming_listings': programming_listings,
        'writing_listings': writing_listings,
        'business_listings': business_listings,
        'digitalm_listings': digitalm_listings,
    }

    if request.GET.get('new_account', '') == 'true':
        context['new_account'] = True

    return render(request, "index.html", context)


User = get_user_model()

def verify_account_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        stored_code = request.session.get('verification_code')

        if code == str(stored_code):
            # Retrieve the stored user data
            user_data = request.session.get('user_data')
            
            if user_data:
                # delegate to create_profile
                # # Create a new user with the saved data
                # user = User.objects.create(
                #     username=user_data['username'],
                #     email=user_data['email'],
                #     password=user_data['password1'],
                #     is_active=True,
                #     is_verified=True
                # )
                # user.set_password(user_data['password1'])  # Set the password correctly
                # user.save()

                request.session['verified_user_data'] = {
                    'username': user_data['username'],
                    'email': user_data['email'],
                    'password': user_data['password1']
                }

                # Clear session data after successful verification
                del request.session['user_data']
                del request.session['verification_code']

                # return redirect('login')  # Redirect to login page after verification
                return redirect('create_profile') # redirect to profile page before login
        else:
            return render(request, 'registration/verification_failed.html')  # If code is incorrect
    
    return render(request, 'registration/verify_account_code.html')

def resend_verification_email(request):
    # Check if user data exists in the session
    user_data = request.session.get('user_data')
    
    if user_data:
        verification_code = random.randint(100000, 999999)  # Generate a new 6-digit code
        request.session['verification_code'] = verification_code

        # Send the verification code via email
        send_mail(
            'Verify your account',
            f'Your new verification code is: {verification_code}',
            'timebartersystem@gmail.com',
            [user_data['email']],
            fail_silently=False,
        )

        # Redirect to the verification page
        return redirect('verify_account_code')
    else:
        return redirect('create_account')  # If user data doesn't exist, redirect to account creation

def create_account(request):
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'create-account.html', {'form': form})
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Temporarily store user data in session until verification is completed
            request.session['user_data'] = form.cleaned_data
            verification_code = random.randint(100000, 999999)  # Generate 6-digit code
            request.session['verification_code'] = verification_code

            # Send the six-digit code via email
            send_mail(
                'Verify your account',
                f'Your verification code is: {verification_code}',
                'timebartersystem@gmail.com',  # Use your verified sender email
                [form.cleaned_data['email']],
                fail_silently=False,
            )

            return redirect('verify_account_code')  # Redirect to verification code entry
        else:
            return render(request, 'create-account.html', {'form': form})


def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_verified:
                login(request, user)
                return redirect('home')
            else:
                return render(request, 'registration/login.html', {'error': 'Please verify your email before logging in.'})
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid username or password.'})
    return render(request, 'registration/login.html')


"""
curl -X POST http://localhost:8000/api/change-password/ \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "current_password": "oldpassword", "new_password": "newpassword"}'

"""
@login_required  # Ensures the user is logged in
def change_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            current_password = data.get('current_password')
            new_password = data.get('new_password')

            user = User.objects.get(username=username)

            # Check if the current password is correct
            if not user.check_password(current_password):
                return JsonResponse({'error': 'Current password is incorrect'}, status=400)
            
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                return JsonResponse({'error': list(e.messages)}, status=400)

            # Set the new password
            user.set_password(new_password)
            user.save()

            return JsonResponse({'status': 'Password changed successfully'}, status=200)

        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        except KeyError:
            return JsonResponse({'error': 'Invalid input, missing fields'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'POST request required'}, status=405)


@login_required  # Ensures the user is logged in
def change_password_page(request):
    return render(request, 'change_password.html')


"""
curl -X POST http://localhost:8000/api/delete-account/ \
     -b "sessionid=<your_session_id>"
"""
@login_required  # Ensures the user is logged in
@csrf_exempt  
def delete_account(request):
    if request.method == 'POST':
        try:
            # Get the logged-in user
            user = request.user

            # Delete the user's account
            user.delete()

            return JsonResponse({'status': 'Account deleted successfully'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'POST request required'}, status=405)


@login_required  # Make sure the user is logged in to access this page
def delete_account_page(request):
    return render(request, 'delete_account.html')


@login_required   # Ensures the user is logged in
# @csrf_exempt  # For handling form submissions via AJAX, use CSRF protection in production
def update_user_settings(request):
    if request.method == 'POST':
        try:
            user = request.user 

            # Get the updated fields from the form or JSON data
            name = request.POST.get('name')
            title = request.POST.get('title')
            location = request.POST.get('location')
            bio = request.POST.get('bio')
            link = request.POST.get('link')
            picture = request.FILES.get('picture')  

            # Update user information only for the fields that are provided
            if name is not None:
                user.name = name
            if title is not None:
                user.title = title
            if location is not None:
                user.location = location
            if bio is not None:
                user.bio = bio
            if link is not None:
                user.link = link
            if picture is not None:
                user.picture = picture  
            user.save()

            return JsonResponse({'status': 'Profile updated successfully'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'POST request required'}, status=405)


@login_required   # Ensures the user is logged in
def user_settings_page(request):
    return render(request, 'user_settings.html')


def user_detail(request, id):
    user = get_object_or_404(User, pk=id)
    data = {
        "email": user.email,  # Include email
        "multiplier": user.multiplier,
        "avg_rating": float(user.avg_rating),
        "name": user.name,
        "picture_url": user.picture.url if user.picture else "",
        "title": user.title,
        "location": user.location,
        "bio": user.bio,
        "link": user.link,
    }
    return JsonResponse(data)


# Display User's information
def user_detail_page(request, id):
    try:
        user = User.objects.get(pk=id)
        # Pass the user object to the template context
        return render(request, 'user_detail.html', {'user': user})
    except User.DoesNotExist:
        # Pass an error message to the template if user is not found
        return render(request, 'user_detail.html', {'error': 'User not found'})


def get_all_listings(request):
    # should be modified if the database of listings is too large
    listings = Listing.objects.all()
    data = []
    for listing in listings:
        data.append(
        data = {
            'id': listing.id,
            'creator': listing.creator.username,  # Assuming creator is a User object
            'category': listing.category.name,  # Assuming Category has a 'name' field
            'tags': [tag.name for tag in listing.tags.all()],  # Get all tags related to the listing
            'title': listing.title,
            'description': listing.description,
            'image': listing.image.url if listing.image else None,  # Get the image URL
            'listing_type': 'Offer' if listing.listing_type else 'Request',  # Convert Boolean to readable value
            'duration': str(listing.duration),  # Convert DurationField to string format
            'posted_at': listing.posted_at.strftime('%Y-%m-%d %H:%M:%S'),  # Format the posted_at timestamp
            'edited_at': listing.edited_at.strftime('%Y-%m-%d %H:%M:%S'),  # Format the edited_at timestamp
        }
        )
    return JsonResponse(data, safe=False)

def get_listing_by_id(request, listing_id):
    try:
        # Fetch the listing by ID
        listing = get_object_or_404(Listing, id=listing_id)
        
        # Prepare the data to return as JSON
        data = {
            'id': listing.id,
            'creator': listing.creator.username,  # Assuming creator is a User object
            'category': listing.category.name,  # Assuming Category has a 'name' field
            'tags': [tag.name for tag in listing.tags.all()],  # Get all tags related to the listing
            'title': listing.title,
            'description': listing.description,
            'image': listing.image.url if listing.image else None,  # Get the image URL
            'listing_type': 'Offer' if listing.listing_type else 'Request',  # Convert Boolean to readable value
            'duration': str(listing.duration),  # Convert DurationField to string format
            'posted_at': listing.posted_at.strftime('%Y-%m-%d %H:%M:%S'),  # Format the posted_at timestamp
            'edited_at': listing.edited_at.strftime('%Y-%m-%d %H:%M:%S'),  # Format the edited_at timestamp
        }

        return JsonResponse(data, status=200)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_responses_for_listing(request, listing_id):
    listing = Listing.objects.get(id=listing_id)
    responses = ListingResponse.objects.filter(listing=listing)
    data = []
    for response in responses:
        data.append(
            {
                "user": response.user.username,
                "message": response.message,
                "status": response.status,
            }
        )
    return JsonResponse(data, safe=False)


def get_availability_for_listing(request, listing_id):
    listing = Listing.objects.get(id=listing_id)
    availabilities = ListingAvailability.objects.filter(listing=listing)
    data = []
    for availability in availabilities:
        data.append(
            {"from_time": availability.from_time, "to_time": availability.to_time}
        )
    return JsonResponse(data, safe=False)



"""
curl -X POST http://localhost:8000/api/create-listing/
     -b "sessionid=<your_session_id>" 
     -F 'title=My New Listing' 
     -F 'category=1' 
     -F 'description=This is a new listing description' 
     -F 'listing_type=True' 
     -F 'duration=2' # in hours
     -F 'tags=1' -F 'tags=2'
     -F 'image=@/path/to/image.jpg'
"""
@login_required  # Ensure the user is logged in
def create_listing(request):
    if request.method == 'POST':
        try:
            # Get the form data
            title = request.POST.get('title')
            category_id = request.POST.get('category')  
            description = request.POST.get('description')
            image = request.FILES.get('image')  # We can only have 1 image per listing
            listing_type = request.POST.get('listing_type')  # Expecting 'True' or 'False'
            duration_in_hours = request.POST.get('duration')  # Expected format: "hours:minutes:seconds"
            tag_ids = request.POST.getlist('tags')  # Expecting a list of tag IDs

            if not title or not category_id or not description or not image or not listing_type or not duration_str:
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            category = get_object_or_404(Category, id=category_id)

            listing_type = listing_type.lower() == 'true'

            try:
                duration_in_hours = int(duration_in_hours)  # Ensure it's an integer
                duration = timedelta(hours=duration_in_hours)  # Convert to timedelta
            except ValueError:
                return JsonResponse({'error': 'Duration must be a valid number'}, status=400)



            listing = Listing.objects.create(
                creator=request.user,  
                title=title,
                category=category,
                description=description,
                image=image,
                listing_type=listing_type,
                duration=duration
            )
            
            listing.save()

            if tag_ids:
                tags = Tag.objects.filter(id__in=tag_ids)
                listing.tags.set(tags)

            return JsonResponse({
                'id': listing.id,
                'title': listing.title,
                'category': listing.category.name,  
                'tags': [tag.name for tag in listing.tags.all()], 
                'description': listing.description,
                'image_url': listing.image.url if listing.image else None,
                'listing_type': 'Offer' if listing.listing_type else 'Request',
                'duration': str(listing.duration)
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'POST request required'}, status=405)

@csrf_exempt
def get_profile(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        user = User.objects.get(username=username)

        profile = {
            'name': user.name,
            'picture': user.picture,
            'title': user.title,
            'location': user.location,
            'bio': user.bio if user.bio else None,
            'link': user.link if user.link else None,
        }

        return JsonResponse({"status": "success", "data": profile}, status=200)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

@csrf_exempt

@login_required
def create_listing_page(request):
    categories = [{'id': choice.value, 'name': choice.label} for choice in Category]
    tags = Tag.objects.all()
    return render(request, 'create_listing.html', {'categories': categories, 'tags': tags})



# Fetch the categories from the database
def get_categories(request):
    # Fetch categories from the TextChoices enum
    categories = [{'id': choice.value, 'name': choice.label} for choice in Category]
    return JsonResponse(categories, safe=False, status=200)


# Fetch the tags from the database
def get_tags(request):
    tags = Tag.objects.all()
    tag_list = [{'id': tag.id, 'name': tag.name} for tag in tags]
    return JsonResponse(tag_list, safe=False, status=200)


def create_profile(request):
    verified_user_data = request.session.get('verified_user_data')
    if not verified_user_data:
        return redirect('create_account')
    
    print("Verified user data:", verified_user_data)
    
    if request.method=='POST':
        form = ProfileCreationForm(request.POST, request.FILES)
        print("Form:", form)
        if form.is_valid():
            print("valid form")
            user = User.objects.create(
                username=verified_user_data['username'],
                email=verified_user_data['email'],
                password=verified_user_data['password1'],
                is_active=True,
                is_verified=True
            )
            user.set_password(verified_user_data['password1'])  # Set the password correctly
            
            user.name = form.cleaned_data['name']
            user.title = form.cleaned_data['title']
            user.location = form.cleaned_data['location']
            user.picture = form.cleaned_data['picture']
            user.bio = form.cleaned_data.get('bio', '')
            user.link = form.cleaned_data.get('link', '')

            user.save()
            del request.session['verified_user_data']

            return redirect('login')  # Redirect to login page
        else:
            print("invalid form")
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    else:
        form = ProfileCreationForm()
    
    return render(request, 'create_profile.html', {'form': form})

@csrf_exempt
def edit_profile(request):
    if request.method=='POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({"status": "success", "message": "Profile edited successfully"}, status=200)
        else:
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)
    else:
        form = ProfileEditForm(instance=request.user)  # pre-fill the form with current user data
    
    # return render(request, 'edit_profile.html', {'form': form})