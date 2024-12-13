function showToast(message, type = 'primary') {
    // const toastContainer = document.getElementById('toast-container');
    const toastElement = document.getElementById('server-response-toast');
    const toastMessage = document.getElementById('toast-message');

    toastMessage.innerText = message;
    toastElement.className = `toast align-items-center text-bg-${type} border-0`;

    const toast = new bootstrap.Toast(toastElement);
    toast.show();
}

document.getElementById('save-settings-button').addEventListener('click', function () {
    const form = document.getElementById('settings-form');
    const formData = new FormData(form);

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
        const qbUrl = formData.get('QB_URL'); // Extract QB_URL directly from the form data
        qbLink.textContent = qbUrl;
        qbLink.href = qbUrl;
        checkQBStatus();
    })
    .catch(error => {
        console.error('Error:', error);
        const messageDiv = document.getElementById('response-message-settings');
        messageDiv.innerHTML = '<div class="alert alert-danger">An error occurred while saving settings.</div>';
        showToast("An error occurred while saving settings.", 'danger');
    });

});

document.addEventListener("DOMContentLoaded", function() 
    {
        checkQBStatus();
        const searchForm = document.getElementById("search-form");
        const resultsContainer = document.getElementById("results-container");
        //const spinner = document.getElementById("spinner"); // Ensure spinner is retrieved
        const searchButton = document.getElementById("searchButton");

        searchForm.addEventListener("submit", function(e) {
            e.preventDefault(); // Prevent the default form submission

            // Show the spinner by removing the 'd-none' class
        //spinner.classList.remove("d-none");

        // modify search button
        searchButton.disabled = true; // Disable the button to prevent multiple clicks
        searchButton.innerHTML = `
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          Searching...
        `;

            // Collect form data
            const formData = new FormData(searchForm);
            const queryParams = new URLSearchParams(formData).toString();
            console.log(formData)
            console.log(queryParams)
            // Send AJAX request
            fetch("/?"+queryParams, {
                method: "GET",
                headers: {
                    "X-Requested-With": "XMLHttpRequest" // Optional for identifying AJAX requests
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.text(); // Get response HTML
                
            })
            .then(html => {
                // Update the results container
                resultsContainer.innerHTML = html;
                
                // showToast("Search successful!", 'success'); // Show success toast
            })
            .catch(error => {
                console.error("Error during AJAX request:", error);
            })
            .finally(() => {
                // Hide the spinner
                //spinner.classList.add("d-none");

                // Reset the search button appearance and text
                searchButton.disabled = false;
                searchButton.innerHTML = "Search";
                const targetDiv = document.getElementById('results-container-wrapper');

                targetDiv.scrollIntoView({
                  behavior: 'smooth' // Optional for smooth scrolling
                });
        });
        });

        // Use event delegation to handle dynamically added buttons
    document.getElementById('results-container').addEventListener('click', function (event) {
        if (event.target && event.target.classList.contains('add-to-qbittorrent-button')) {
            event.preventDefault();
            checkQBStatus();
            const button = event.target;
            const form = button.closest('form');
            const formData = new FormData(form);
            const messageDiv = form.nextElementSibling;

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
                // const parentElement = document.querySelector("#qbAccordionCollapse"); // Assuming this is the parent container for the alert
                // const alertSelector = ".alert.alert-warning[role='alert']";
                
                
                if (statusSpan) {
                    // Update the status text and style
                    statusSpan.textContent = data.status === "success" ? "CONNECTED" : "NOT CONNECTED";
                    statusSpan.className = data.status === "success" ? "text-success" : "text-danger";
    
       
                    }
                    
                    // Select all elements with the class 'response-message-result'
                    const elements = document.querySelectorAll('.response-message-result');
    
                    // Loop through and clear the content of each element
                    elements.forEach(element => {
                      element.innerHTML = '';
                    });
    
                    // Optionally show a toast with the response message
                    const toastType = data.status === "success" ? "success" : "danger";
                    showToast(data.message, toastType);
    
                    // Enable or disable the Add to Qbittorrent buttons based on the connection status
                    const buttons = document.getElementsByClassName('add-to-qbittorrent-button');
                    Array.prototype.forEach.call(buttons, function(button) {
                        button.disabled = data.status !== "success"; // Disable if not connected
                        
                    });
    
                    // disable tooltips
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
                // const parentElement = document.querySelector("#qbAccordionCollapse"); // Assuming this is the parent container for the alert
                // const alertSelector = ".alert.alert-warning[role='alert']";
                // const alertElements = document.querySelectorAll(alertSelector); // Select all alert elements
    
                if (statusSpan) {
                    statusSpan.textContent = "NOT CONNECTED";
                    statusSpan.className = "text-danger";
                }
    
                // // Ensure at least one alert element is present
                // if (alertElements.length === 0 && parentElement) {
                //     const alertElement = document.createElement("div");
                //     alertElement.className = "alert alert-warning mt-2";
                //     alertElement.role = "alert";
                //     alertElement.textContent = "Unable to connect to qBittorrent. Please check your connection settings.";
                //     parentElement.appendChild(alertElement);
                // }
    
                // Select all elements with the class 'response-message-result'
                const elements = document.querySelectorAll('.response-message-result');
    
                // Loop through and add a Bootstrap alert message
                elements.forEach(element => {
                  element.innerHTML = `
                    <div class="alert alert-warning" role="alert">
                      qBittorrent is not connected. Check your connection settings.
                    </div>
                  `;
                });
    
                // Disable Add to Qbittorrent buttons on error
                const buttons = document.getElementsByClassName('add-to-qbittorrent-button');
                Array.prototype.forEach.call(buttons, function(button) {
                    button.disabled = true;
                });
    
                // enable tooltips
                const enableTooltips = () => {
                  // Select all buttons with the specific class
                  document.querySelectorAll('.add-to-qbittorrent-button').forEach(button => {
                      const parentDiv = button.closest('.d-grid');
    
                      if (parentDiv) {
                          // Add tooltip attributes
                          parentDiv.setAttribute('data-bs-toggle', 'tooltip');
                          parentDiv.setAttribute('title', 'qBittorrent is not connected. Check your connection settings.');
    
                          // Initialize the Bootstrap tooltip
                          new bootstrap.Tooltip(parentDiv);
                      }
                  });
              };
    
                // Call the function to enable tooltips
                enableTooltips();
    
                // clear categories
                const dropdowns = document.querySelectorAll('.category-dropdown');
                // Iterate through dropdowns and populate each
                dropdowns.forEach(dropdown => {
                    // Clear existing options
                    dropdown.innerHTML = '';
                    // Add a default placeholder option
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Category';
                    dropdown.appendChild(placeholder);
                });
    
                showToast("Error fetching QB_STATUS", "danger");
            });
    }
    
    function refreshCategories() {
        fetch('/qb/categories', { cache: "no-store" }) // Replace with your actual endpoint
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to fetch categories: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Find all category dropdowns
                const dropdowns = document.querySelectorAll('.category-dropdown');
    
                // Check if categories are returned
                const hasCategories = data && Object.keys(data).length > 0;
    
                // Retrieve the default category value from the input field
                const defaultCategoryInput = document.getElementById('QB_CATEGORY');
                const defaultCategory = defaultCategoryInput ? defaultCategoryInput.value : '';
    
                // Iterate through dropdowns and populate each
                dropdowns.forEach(dropdown => {
                    // Clear existing options
                    dropdown.innerHTML = '';
    
                    // Add a default placeholder option
                    const placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = 'Category';
                    dropdown.appendChild(placeholder);
    
                    // Populate dropdown if categories exist
                    if (hasCategories) {
                        for (const key in data) {
                            if (Object.prototype.hasOwnProperty.call(data, key)) {
                                const category = data[key]; // e.g., { name: 'prowlarr', savePath: '/prowlarr' }
                                const option = document.createElement('option');
                                option.value = category.name; // Use the category name as the value
                                option.textContent = category.name; // Display the category name
                                dropdown.appendChild(option);
                            }
                        }
                    }
    
                    // Select the default category if it matches
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
    
                // Clear dropdowns on error
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
  
        // Observe the status element for changes in its text
        observer.observe(statusElement, { characterData: true, subtree: true, childList: true });
    }
  
  
    // Start monitoring QB status on page load
    document.addEventListener("DOMContentLoaded", monitorDOMForQBStatus);

// Function to check QBittorrent status
// function checkQBStatus() {
//     fetch('/qb/status', { cache: "no-store" })
//         .then(response => {
//             if (!response.ok) {
//                 throw new Error(`Network response was not ok: ${response.status}`);
//             }
//             return response.json();
//         })
//         .then(data => {
//             const statusSpan = document.querySelector("#qbAccordionCollapse .text-success, #qbAccordionCollapse .text-danger");
//             if (statusSpan) {
//                 statusSpan.textContent = data.status === "success" ? "CONNECTED" : "NOT CONNECTED";
//                 statusSpan.className = data.status === "success" ? "text-success" : "text-danger";
//             }
//             showToast(data.message, data.status === "success" ? "success" : "danger");
//         })
//         .catch(error => {
//             console.error("Error fetching QB_STATUS:", error);
//             showToast("Error fetching QB_STATUS", "danger");
//         });
// }