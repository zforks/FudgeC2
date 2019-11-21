import time
import uuid
import bcrypt

from Data.models import Users
from Data.CampaignLogging import CampaignLoggingDecorator

CL = CampaignLoggingDecorator()


class DatabaseUser:

    def __init__(self, source_database, session):
        # TODO: Check sesion type
        self.Session = session
        self.db_methods = source_database

    # Test / Remove / Refactor
    @staticmethod
    def __hash_cleartext_password__(password):
        # Hashed a clear text password ready for insertion into the database
        password_bytes = password.encode()
        hashedpassword = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        if bcrypt.checkpw(password_bytes, hashedpassword):
            return hashedpassword
        else:
            return False

    def __update_last_logged_in__(self, email):
        self.Session.query(Users).filter(Users.user_email == email).update({"last_login": (time.time())})
        self.Session.commit()
        return True

    # Test / Remove / Refactor
    def add_new_user(self, username, password, admin=False):
        # -- TODO: This needs a more robust response Try/Except.
        query = self.Session.query(Users.password, Users.uid).filter(Users.user_email == username).all()
        for x in query:
            return False
        users = Users(user_email=username,
                      password=self.db_methods.__hash_cleartext_password__(password),
                      admin=admin,
                      last_login=time.time())
        self.Session.add(users)
        self.Session.commit()
        self.db_methods.app_logging("auth", f"New user created: {username}")
        return True

    # Test / Remove / Refactor
    def User_ChangePasswordOnFirstLogon(self, guid, current_password, new_password):
        user_object = self.Session.query(Users).filter(Users.first_logon_guid == guid).first()
        if user_object is None:
            return False
        else:
            if bcrypt.checkpw(current_password.encode(), user_object.password):
                hashedpassword = self.__hash_cleartext_password__(new_password)
                self.Session.query(Users).filter(Users.first_logon_guid == guid).update({"password": hashedpassword, "first_logon": 1})
                self.Session.commit()
                updated_user_object = self.Session.query(Users).filter(Users.password == hashedpassword).first()
                return updated_user_object
            else:
                return False

    # Test / Remove / Refactor
    def User_IsUserAdminAccount(self, email):
        user_object = self.db_methods.__get_user_object_from_email__(email)
        if user_object:
            if int(user_object.admin) == 1:
                return True
        return False

    # Test / Remove / Refactor
    def Get_UserFirstLogonGuid(self, email):
        pre_guid = str(uuid.uuid4())
        self.Session.query(Users).filter(Users.user_email == email).update({"first_logon_guid": pre_guid})
        self.Session.commit()
        return pre_guid

    def user_login(self, email, password):
        # Auths a user and returns user object
        user = self.Session.query(Users).filter(Users.user_email == email).first()
        if user is not None:
            if bcrypt.checkpw(password.encode(), user.password):
                if user.active_account == "False":
                    self.db_methods.app_logging("auth", f"Failed login attempt for disabled account: {email} ")
                    return False

                self.__update_last_logged_in__(email)
                self.db_methods.app_logging("auth", f"Successful login for user: {email}")

                return user
            else:
                self.db_methods.app_logging("auth", f"Failed login attempt for user {email} ")
                return False
        else:
            return False
    def change_account_active_state(self, user, state):
        '''
        :param user: Account of the user whos state is to be changes
        :param state: True or False boolean.
        :return: Boolean return depending on the sucess of the DB update.
        '''
        try:
            self.Session.query(Users).filter(Users.user_email == user).update({"active_account": state})
            self.Session.commit()
            return True
        except Exception as e:
            print("Error: account not found, or state not changed.")
            return False

    def Get_UserObject(self, email):
        # Returns the user object based on username/email.
        user = self.Session.query(Users).filter(Users.user_email == email).first()
        return user
