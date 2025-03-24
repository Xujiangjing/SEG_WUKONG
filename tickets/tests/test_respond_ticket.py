from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory


def test_respond_ticket():
    request = RequestFactory().post('/ticket/respond/')  # Simulate a request
    setattr(request, 'session', {})  # Add session storage
    setattr(request, '_messages', FallbackStorage(request))  # Attach message storage

    messages.success(request, "A response has been sent for your ticket #123.")  # Add message

    # Print all messages to verify
    for message in request._messages:
        print(f"Message Type: {message.tags} | Message: {message}")

# Run the function to test
test_respond_ticket()
