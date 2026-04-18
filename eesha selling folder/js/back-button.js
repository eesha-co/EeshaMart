// Create and initialize back button functionality
function initializeBackButton() {
    // Create the back button element
    const backButton = document.createElement('button');
    backButton.className = 'back-button';
    backButton.setAttribute('aria-label', 'Go back');
    backButton.innerHTML = `
        <i class="fas fa-arrow-left"></i>
        <span>Back</span>
    `;

    // Add click handler
    backButton.addEventListener('click', () => {
        // Check if there's a previous page in the history
        if (window.history.length > 1) {
            window.history.back();
        } else {
            // Fallback to index.html if no history
            window.location.href = 'index.html';
        }
    });

    // Check if page has sidebar
    const hasSidebar = document.querySelector('.sidebar') !== null;
    if (hasSidebar) {
        document.body.classList.add('has-sidebar');
    }

    // Add to document
    document.body.appendChild(backButton);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeBackButton);