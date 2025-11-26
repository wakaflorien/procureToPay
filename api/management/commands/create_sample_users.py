"""
Management command to create sample users for testing
"""
from django.core.management.base import BaseCommand
from api.models import User


class Command(BaseCommand):
    help = 'Create sample users for testing'

    def handle(self, *args, **options):
        users_data = [
            {
                'username': 'staff1',
                'email': 'staff1@example.com',
                'password': 'staff123',
                'role': 'staff',
                'first_name': 'John',
                'last_name': 'Staff',
            },
            {
                'username': 'approver1',
                'email': 'approver1@example.com',
                'password': 'approver123',
                'role': 'approver_level_1',
                'first_name': 'Jane',
                'last_name': 'Approver1',
            },
            {
                'username': 'approver2',
                'email': 'approver2@example.com',
                'password': 'approver123',
                'role': 'approver_level_2',
                'first_name': 'Bob',
                'last_name': 'Approver2',
            },
            {
                'username': 'finance1',
                'email': 'finance1@example.com',
                'password': 'finance123',
                'role': 'finance',
                'first_name': 'Alice',
                'last_name': 'Finance',
            },
        ]

        for user_data in users_data:
            username = user_data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User {username} already exists, skipping...')
                )
            else:
                User.objects.create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created user: {username}')
                )

        self.stdout.write(
            self.style.SUCCESS('\nSample users created successfully!')
        )
        self.stdout.write(
            self.style.SUCCESS('\nLogin credentials:')
        )
        for user_data in users_data:
            self.stdout.write(
                f"  {user_data['username']} / {user_data['password']} ({user_data['role']})"
            )

