function toggleInstances(groupIndex) {
    const container = document.getElementById('instances-' + groupIndex);
    const icon = document.getElementById('toggle-' + groupIndex);
    
    if (container.classList.contains('expanded')) {
        container.classList.remove('expanded');
        icon.classList.remove('expanded');
    } else {
        container.classList.add('expanded');
        icon.classList.add('expanded');
    }
}

function toggleRulesList() {
    const rulesList = document.getElementById('rules-list');
    rulesList.classList.toggle('show');
}

function jumpToRule(groupIndex) {
    // Close the rules list
    toggleRulesList();
    
    // Scroll to the corresponding rule group
    const ruleGroup = document.querySelector(`[data-group-index="${groupIndex}"]`);
    if (ruleGroup) {
        ruleGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Automatically expand the rule group
        const container = document.getElementById('instances-' + groupIndex);
        const icon = document.getElementById('toggle-' + groupIndex);
        if (container && !container.classList.contains('expanded')) {
            container.classList.add('expanded');
            icon.classList.add('expanded');
        }
        
        // Add highlight effect
        ruleGroup.style.boxShadow = '0 0 20px rgba(233, 30, 99, 0.3)';
        setTimeout(() => {
            ruleGroup.style.boxShadow = '';
        }, 2000);
    }
}

// Back-to-top button functionality
function initBackToTopButton() {
    const backToTopBtn = document.getElementById('back-to-top');
    if (!backToTopBtn) return;
    
    // Listen to scroll events
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.classList.add('show');
        } else {
            backToTopBtn.classList.remove('show');
        }
    });
    
    // Click to scroll back to top
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Click modal backdrop to close
document.addEventListener('DOMContentLoaded', function() {
    const rulesListContainer = document.getElementById('rules-list');
    if (rulesListContainer) {
        rulesListContainer.addEventListener('click', function(e) {
            if (e.target === rulesListContainer) {
                toggleRulesList();
            }
        });
    }
    
    // ESC key closes modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const rulesList = document.getElementById('rules-list');
            if (rulesList && rulesList.classList.contains('show')) {
                toggleRulesList();
            }
        }
    });
    
    // Initialize back-to-top button
    initBackToTopButton();
});