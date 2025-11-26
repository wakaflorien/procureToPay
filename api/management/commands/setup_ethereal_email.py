"""
Management command to set up Ethereal Email for testing
Creates a test account and displays SMTP credentials
"""
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Set up Ethereal Email account for testing and display SMTP credentials'

    def add_arguments(self, parser):
        parser.add_argument(
            '--save-to-env',
            action='store_true',
            help='Save credentials to .env file (creates if not exists)',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Ethereal email username (from https://ethereal.email/create)',
        )
        parser.add_argument(
            '--pass',
            dest='password',
            type=str,
            help='Ethereal email password (from https://ethereal.email/create)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up Ethereal Email for testing...\n'))
        
        # Check if credentials are already provided
        email_user = os.getenv('EMAIL_HOST_USER', '')
        email_pass = os.getenv('EMAIL_HOST_PASSWORD', '')
        email_host = os.getenv('EMAIL_HOST', '')
        
        # Check if credentials provided via command line
        if options.get('user') and options.get('password'):
            account = {'user': options['user'], 'pass': options['password']}
            self.stdout.write(self.style.SUCCESS('✓ Using provided credentials!\n'))
        elif email_host == 'smtp.ethereal.email' and email_user and email_pass:
            self.stdout.write(self.style.SUCCESS('✓ Ethereal Email credentials found in environment!\n'))
            account = {'user': email_user, 'pass': email_pass}
        else:
            # Try to create account via API (may not always work)
            self.stdout.write(self.style.WARNING('Attempting to create Ethereal account via API...'))
            account = None
            
            try:
                # Try the Ethereal API endpoint
                response = requests.post(
                    'https://api.nodemailer.com/user',
                    headers={'Content-Type': 'application/json'},
                    json={},
                    timeout=10
                )
                
                if response.status_code == 200:
                    account = response.json()
                    if account.get('user') and account.get('pass'):
                        self.stdout.write(self.style.SUCCESS('✓ Account created via API!\n'))
                else:
                    raise requests.RequestException(f"API returned status {response.status_code}")
                    
            except requests.RequestException:
                # API failed - provide manual instructions
                self.stdout.write(self.style.WARNING('⚠️  API account creation unavailable.\n'))
                self.stdout.write(self.style.SUCCESS('📝 Manual Setup Instructions:\n'))
                self.stdout.write(self.style.WARNING('=' * 60))
                self.stdout.write('1. Go to: https://ethereal.email/create')
                self.stdout.write('2. Click "Create Account" button')
                self.stdout.write('3. Copy your username and password')
                self.stdout.write('4. Run this command with credentials:')
                self.stdout.write(self.style.SUCCESS('   python manage.py setup_ethereal_email --user YOUR_USERNAME --pass YOUR_PASSWORD'))
                self.stdout.write(self.style.WARNING('=' * 60))
                self.stdout.write('\nOr set environment variables manually:\n')
                self._display_config_template()
                return
            
            if not account or not account.get('user') or not account.get('pass'):
                raise ValueError("Failed to get valid credentials")
        
        # Display credentials (for all successful paths)
        self.stdout.write(self.style.SUCCESS('\n✓ Ethereal Email configured successfully!\n'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.SUCCESS('SMTP Configuration:'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(f"EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
        self.stdout.write(f"EMAIL_HOST=smtp.ethereal.email")
        self.stdout.write(f"EMAIL_PORT=587")
        self.stdout.write(f"EMAIL_USE_TLS=True")
        self.stdout.write(f"EMAIL_HOST_USER={account['user']}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD={account['pass']}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL={account['user']}")
        self.stdout.write(self.style.WARNING('=' * 60))
        
        # Display web interface URL
        self.stdout.write(self.style.SUCCESS('\n📧 View emails at:'))
        self.stdout.write(self.style.SUCCESS(f"   https://ethereal.email/login"))
        self.stdout.write(self.style.SUCCESS(f"   Username: {account['user']}"))
        self.stdout.write(self.style.SUCCESS(f"   Password: {account['pass']}"))
        
        # Save to .env if requested
        if options['save_to_env']:
            env_file = os.path.join(settings.BASE_DIR, '.env')
            env_exists = os.path.exists(env_file)
            
            with open(env_file, 'a' if env_exists else 'w') as f:
                if not env_exists:
                    f.write('# Ethereal Email Configuration\n')
                f.write('\n# Ethereal Email (for testing)\n')
                f.write('EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend\n')
                f.write('EMAIL_HOST=smtp.ethereal.email\n')
                f.write('EMAIL_PORT=587\n')
                f.write('EMAIL_USE_TLS=True\n')
                f.write(f'EMAIL_HOST_USER={account["user"]}\n')
                f.write(f'EMAIL_HOST_PASSWORD={account["pass"]}\n')
                f.write(f'DEFAULT_FROM_EMAIL={account["user"]}\n')
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Credentials saved to {env_file}'))
            self.stdout.write(self.style.WARNING('\n⚠️  Remember to restart your Django server for changes to take effect!'))
        
        self.stdout.write(self.style.WARNING('\n⚠️  Note: Ethereal accounts are temporary and may expire after inactivity.'))
        self.stdout.write(self.style.WARNING('   For production, use a real SMTP service (Gmail, SendGrid, etc.).'))
    
    def _display_config_template(self):
        """Display configuration template"""
        self.stdout.write(self.style.SUCCESS('\nEMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend'))
        self.stdout.write('EMAIL_HOST=smtp.ethereal.email')
        self.stdout.write('EMAIL_PORT=587')
        self.stdout.write('EMAIL_USE_TLS=True')
        self.stdout.write('EMAIL_HOST_USER=your-username@ethereal.email')
        self.stdout.write('EMAIL_HOST_PASSWORD=your-password')
        self.stdout.write('DEFAULT_FROM_EMAIL=your-username@ethereal.email\n')

