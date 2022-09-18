from .exceptions import InvalidCredentials,WaitTimeError,UserNotExists
from django.contrib.auth import authenticate,login
from rest_framework.response import Response
from django.core.cache import cache
from random import randint
from .tasks import send_mail_celery
from .models import User

class DukanAuthUtils:
    pass


class DukanAuth:

    def LoginUser(self,request):
        data = request.data
        username = data.get('username')
        password = data.get('password')
        if username and password:
            if '@' in username:
                try:
                    username = User.objects.get(email=username).username
                except:
                    raise InvalidCredentials()
            user = authenticate(request,username=username,password=password)
            if user is None:
                raise InvalidCredentials()
            else:
                if user.two_factor_auth:
                    if cache.get(user.email):
                        raise WaitTimeError()

                    # procced for two factor
                    otp = randint(100000,999999)

                    context = {
                        "password": password,
                        "otp": otp
                    }
                    
                    cache.set(user.email,context,300)

                    # send the mail using celery

                    send_mail_celery.delay(
                        to=[user.email],

                        subject=f'''Hey {user.first_name}! Your OTP is here for login on apnidukan.''',

                        message = f"""Your One time Password for login is {otp}.\n\nPlease Don't share the
                                    password with anyone.\n\nPlease Change Your password immediatly in case it's not you.\n\nThanks & Regards\nTeam Apni Dukaan"""

                    )

                    return Response({'status':200,'message':'OTP delivered successfully.'})

                else:
                    login(request,user)
                    return Response({'status':200,'message':'User logged in successfully.'})
        else:
            raise InvalidCredentials("Empty Credentials Provided.")


    
    def ValidateOTPLogin(self,request):
        username = request.data.get('username')
        try:
            otp = int(request.data.get('otp').strip())
        except:
            return Response({'status':400,'message':'Empty OTP or Invalid OTP provided.'})
        if '@' not in username:
            og_user = User.objects.get(username=username)
            email = og_user.email
        else:
            og_user = User.objects.get(email=username)
            email = username
            username = og_user.username
        data = cache.get(email)
        if not data:
            raise UserNotExists()

        user = authenticate(username=username,password=data["password"])

        if user is None:
            return Response({'status':400,'message':'Invalid Credentials.'})
        if otp != data["otp"]:
            return Response({'status':400,'message':'OTP did not match'})
        
        login(request,user)
        cache.delete(email)
        return Response({'status':200,'message':'successfully logged in.'})