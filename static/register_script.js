// Handle registration form submission
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('registerForm');
    
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            
            // Get username from form and store in sessionStorage
            const username = document.getElementById('username').value;
            sessionStorage.setItem('username', username);
            
            // Get form data
            const formData = new FormData(registerForm);
            
            // Submit to backend
            fetch('/register', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'include', // Include cookies/session for Flask-Login
                redirect: 'follow' // Allow fetch to follow redirects
            })
            .then(async response => {
                // Check if response was redirected (success case)
                if (response.redirected || response.status === 200) {
                    // Success - redirect to dashboard
                    window.location.href = '/';
                    return;
                }
                
                // Check if it's an error status (4xx or 5xx)
                if (!response.ok) {
                    // Try to get error message - check content type first
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        // It's JSON, parse it
                        try {
                            const data = await response.json();
                            alert('Error: ' + (data.error || 'Registration failed'));
                            return;
                        } catch (e) {
                            console.error('Failed to parse JSON error:', e);
                        }
                    }
                    // Not JSON (probably HTML error page), show generic error
                    alert('Error: Registration failed. Please try again.');
                    return;
                }
                
                // If we get here and response is OK, redirect anyway
                window.location.href = '/';
            })
            .catch(error => {
                console.error('Registration error in catch block:', error);
                console.error('Error message:', error.message);
                console.error('Error stack:', error.stack);
                // On any error, try redirecting (user might have been created)
                // This handles cases where redirect causes issues
                window.location.href = '/';
            });
        });
    }
});

