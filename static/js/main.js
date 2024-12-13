/**
 * Displays a toast message on the screen.
 * @param {string} message - The message to display in the toast.
 * @param {string} type - The Bootstrap contextual class for the toast, e.g., 'success', 'danger'. Default is 'primary'.
 */
function showToast(message, type = 'primary') {
    // Get the toast element and message container
    const toastElement = document.getElementById('server-response-toast');
    const toastMessage = document.getElementById('toast-message');

    // Set the message and style of the toast
    toastMessage.innerText = message;
    toastElement.className = `toast align-items-center text-bg-${type} border-0`;

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

document.getElementById('save-settings-button').addEventListener('click', function () {
    // Retrieve the form and its data
    const form = document.getElementById('settings-form');
    const formData = new FormData(form);

    // Send a POST request to update settings
    fetch('/update_settings', {
        method: 'POST',
        body: formData,
    })
        .then(response => response.json())
        .then(data => {
            const messageDiv = document.getElementById('response-message-settings');
            if (data.status === 'success') {
                messageDiv.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                showToast(data.message, 'success');
            } else {
                messageDiv.innerHTML = '<div class="alert alert-danger">Failed to save settings. Please try again.</div>';
                showToast("Failed to save settings. Please try again.", 'danger');
            }

            // Update the QB URL in the accordion
            const qbLink = document.getElementById('qbLink');
            const qbUrl = formData.get('QB_URL');
            qbLink.textContent = qbUrl;
            qbLink.href = qbUrl;

            // Check the QBittorrent status
            checkQBStatus();
        })
        .catch(error => {
            console.error('Error:', error);
            const messageDiv = document.getElementById('response-message-settings');
            messageDiv.innerHTML = '<div class="alert alert-danger">An error occurred while saving settings.</div>';
            showToast("An error occurred while saving settings.", 'danger');
        });
});

document.addEventListener("DOMContentLoaded", function () {
    // Initial check of QBittorrent status
    checkQBStatus();

    const searchForm = document.getElementById("search-form");
    const resultsContainer = document.getElementById("results-container");
    const searchButton = document.getElementById("searchButton");

    searchForm.addEventListener("submit", function (e) {
        e.preventDefault(); // Prevent the default form submission

        // Modify search button to show loading state
        searchButton.disabled = true;
        searchButton.innerHTML = `
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          Searching...
        `;

        // Collect form data and construct query parameters
        const formData = new FormData(searchForm);
        const queryParams = new URLSearchParams(formData).toString();

        // Send AJAX request to perform search
        fetch("/?" + queryParams, {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.text(); // Get response HTML
            })
            .then(html => {
                // Update the results container with the HTML response
                resultsContainer.innerHTML = html;
            })
            .catch(error => {
                console.error("Error during AJAX request:", error);
            })
            .finally(() => {
                // Reset the search button appearance and re-enable it
                searchButton.disabled = false;
                searchButton.innerHTML = "Search";

                // Scroll to the results container
                const targetDiv = document.getElementById('results-container-wrapper');
                targetDiv.scrollIntoView({
                    behavior: 'smooth'
                });
            });
    });

    // Event delegation to handle dynamically added buttons for adding torrents
    document.getElementById('results-container').addEventListener('click', function (event) {
        if (event.target && event.target.classList.contains('add-to-qbittorrent-button')) {
            event.preventDefault();
            checkQBStatus();
            const button = event.target;
            const form = button.closest('form');
            const formData = new FormData(form);
            const messageDiv = form.nextElementSibling;

            // Send a POST request to add torrent to QBittorrent
            fetch('/add_to_qbittorrent', {
                method: 'POST',
                body: formData,
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        messageDiv.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';
                        showToast(data.message, 'success');
                    } else {
                        messageDiv.innerHTML = '<div class="alert alert-danger">Failed to add torrent. Please try again.</div>';
                        showToast("Failed to add torrent. Please try again.", 'danger');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    messageDiv.innerHTML = '<div class="alert alert-danger">An error occurred while adding the torrent.</div>';
                    showToast("An error occurred while adding the torrent.", 'danger');
                });
        }
    });
});

/**
 * Checks the connection status of QBittorrent and updates the UI accordingly.
 */
function checkQBStatus() {
    fetch('/qb/status', { cache: "no-store" })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const statusSpan = document.querySelector("#qbAccordionCollapse .text-success, #qbAccordionCollapse .text-danger");
            if (statusSpan) {
                statusSpan.textContent = data.status === "success" ? "CONNECTED" : "NOT CONNECTED";
                statusSpan.className = data.status === "success" ? "text-success" : "text-danger";
            }

            // Clear response messages
            const elements = document.querySelectorAll('.response-message-result');
            elements.forEach(element => {
                element.innerHTML = '';
            });

            // Show a toast with the response message
            const toastType = data.status === "success" ? "success" : "danger";
            showToast(data.message, toastType);

            // Enable or disable 'Add to Qbittorrent' buttons based on connection status
            const buttons = document.getElementsByClassName('add-to-qbittorrent-button');
            Array.prototype.forEach.call(buttons, function (button) {
                button.disabled = data.status !== "success";
            });

            // Disable tooltips
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(element => {
                element.removeAttribute('data-bs-toggle');
                element.removeAttribute('title');
            });

            // Refresh categories if connected
            if (data.status === "success") {
                refreshCategories();
            }
        })
        .catch(error => {
            console.error("Error fetching QB_STATUS:", error);

            const statusSpan = document.querySelector("#qbAccordionCollapse .text-success, #qbAccordionCollapse .text-danger");
            if (statusSpan) {
                statusSpan.textContent = "NOT CONNECTED";
                statusSpan.className = "text-danger";
            }

            // Add warning message to response message elements
            const elements = document.querySelectorAll('.response-message-result');
            elements.forEach(element => {
                element.innerHTML = `
                <div class="alert alert-warning" role="alert">
                  qBittorrent is not connected. Check your connection settings.
                </div>
              `;
            });

            // Disable 'Add to Qbittorrent' buttons on error
            const buttons = document.getElementsByClassName('add-to-qbittorrent-button');
            Array.prototype.forEach.call(buttons, function (button) {
                button.disabled = true;
            });

            // Enable tooltips for disconnected state
            const enableTooltips = () => {
                document.querySelectorAll('.add-to-qbittorrent-button').forEach(button => {
                    const parentDiv = button.closest('.d-grid');
                    if (parentDiv) {
                        parentDiv.setAttribute('data-bs-toggle', 'tooltip');
                        parentDiv.setAttribute('title', 'qBittorrent is not connected. Check your connection settings.');
                        new bootstrap.Tooltip(parentDiv);
                    }
                });
            };

            enableTooltips();

            // Clear category dropdowns
            const dropdowns = document.querySelectorAll('.category-dropdown');
            dropdowns.forEach(dropdown => {
                dropdown.innerHTML = '';
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = 'Category';
                dropdown.appendChild(placeholder);
            });

            showToast("Error fetching QB_STATUS", "danger");
        });
}

/**
 * Refreshes the categories from the server and updates category dropdowns.
 */
function refreshCategories() {
    fetch('/qb/categories', { cache: "no-store" })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch categories: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const dropdowns = document.querySelectorAll('.category-dropdown');
            const hasCategories = data && Object.keys(data).length > 0;
            const defaultCategoryInput = document.getElementById('QB_CATEGORY');
            const defaultCategory = defaultCategoryInput ? defaultCategoryInput.value : '';

            dropdowns.forEach(dropdown => {
                dropdown.innerHTML = '';
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = 'Category';
                dropdown.appendChild(placeholder);

                if (hasCategories) {
                    for (const key in data) {
                        if (Object.prototype.hasOwnProperty.call(data, key)) {
                            const category = data[key];
                            const option = document.createElement('option');
                            option.value = category.name;
                            option.textContent = category.name;
                            dropdown.appendChild(option);
                        }
                    }
                }

                if (defaultCategory) {
                    const options = dropdown.options;
                    for (let i = 0; i < options.length; i++) {
                        if (options[i].value === defaultCategory) {
                            options[i].selected = true;
                            break;
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error("Error refreshing categories:", error);

            const dropdowns = document.querySelectorAll('.category-dropdown');
            dropdowns.forEach(dropdown => {
                dropdown.innerHTML = '';
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = 'Category';
                dropdown.appendChild(placeholder);
            });
        });
}

/**
 * Monitors the DOM for changes in the QBittorrent connection status and shows a toast if it changes to "NOT CONNECTED".
 */
function monitorDOMForQBStatus() {
    const statusElement = document.querySelector("#qbAccordionCollapse .text-success, #qbAccordionCollapse .text-danger");

    if (!statusElement) {
        console.error("Status element not found in the DOM.");
        return;
    }

    let lastStatus = statusElement.textContent.trim();

    const observer = new MutationObserver((mutationsList) => {
        mutationsList.forEach((mutation) => {
            if (mutation.type === "characterData" || mutation.type === "childList") {
                const currentStatus = statusElement.textContent.trim();

                if (currentStatus === "NOT CONNECTED" && currentStatus !== lastStatus) {
                    showToast("QBittorrent is NOT CONNECTED", "danger");
                }

                lastStatus = currentStatus;
            }
        });
    });

    observer.observe(statusElement, { characterData: true, subtree: true, childList: true });
}

// Start monitoring QB status on page load
document.addEventListener("DOMContentLoaded", monitorDOMForQBStatus);

