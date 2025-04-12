// Keep your existing Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyCj4PgVbGNf1faHSwXekGj4Hg2FHNuAdvo",
    authDomain: "craftecho.firebaseapp.com",
    projectId: "craftecho",
    storageBucket: "craftecho.firebasestorage.app",
    messagingSenderId: "859530568811",
    appId: "1:859530568811:web:9b64c5283357d2b1bb7d2e",
    measurementId: "G-ED411QMMBY"
  };
  
  if (!firebase.apps.length) {
      firebase.initializeApp(firebaseConfig);
  }
  const auth = firebase.auth();
  const db = firebase.firestore();
  
  // Global variables
  window.currentLearner = null; // Store basic learner info
  let assignedCourse = null;    // Store assigned course details
  
  // --- Authentication Listener ---
  auth.onAuthStateChanged(user => {
    if (user) {
      console.log("User logged in:", user.uid);
      window.currentLearner = {
        uid: user.uid,
        email: user.email,
        name: user.displayName || user.email // Initial name
      };
  
      // Update greeting immediately
      updateGreeting(window.currentLearner.name);
  
      // Load learner-specific data (profile, assigned mentor/course)
      loadLearnerProfile(); // Load profile first
      fetchMatchedCourses(); // Fetch matched courses
  
    } else {
      // User is signed out
      console.log("User logged out or not logged in.");
      // Redirect to login page if not authenticated
      window.location.href = "/signin"; // Adjust redirect as needed
    }
  });
  
  function updateGreeting(name) {
    const learnerNameSpan = document.getElementById('learner-name');
    if (learnerNameSpan) {
        learnerNameSpan.textContent = name || "Learner"; // Fallback name
    }
}

// --- Populate Profile Modal ---
function populateProfileModal(learnerData) {
    console.log("Populating profile modal with:", learnerData);
    const emailInput = document.getElementById('learnerEmail');
    const nameInput = document.getElementById('learnerName');
    const ageInput = document.getElementById('learnerAge');
    const genderSelect = document.getElementById('learnerGender');
    const skillInterestSelect = document.getElementById('skillinterest');
    const skillLevelSelect = document.getElementById('skilllevel');
    const preferredDaysSelect = document.getElementById('preferreddays');
    const preferredTimeSelect = document.getElementById('preferredtime');
    const goalsTextarea = document.getElementById('learnerGoals');

    if (emailInput) {
        emailInput.value = learnerData?.email || window.currentLearner?.email || ''; // Set email value
    }
    if (nameInput) {
        nameInput.value = learnerData?.name || '';
    }
    if (ageInput) {
        ageInput.value = learnerData?.age || '';
    }
    if (genderSelect) {
        genderSelect.value = learnerData?.gender || '';
    }
    if (skillInterestSelect) {
        skillInterestSelect.value = learnerData?.skillinterest || '';
    }
    if (skillLevelSelect) {
        skillLevelSelect.value = learnerData?.skilllevel || '';
    }
    if (preferredDaysSelect) {
        preferredDaysSelect.value = learnerData?.preferreddays || '';
    }
    if (preferredTimeSelect) {
        preferredTimeSelect.value = learnerData?.preferredtime || '';
    }
    if (goalsTextarea) {
        goalsTextarea.value = learnerData?.goals || '';
    }
}

// --- Load Learner Profile (Only fetches profile, does not trigger matching) ---
function loadLearnerProfile() {
    if (!window.currentLearner || !window.currentLearner.uid) {
        console.log("Cannot load profile: currentLearner or UID missing.");
        // Optionally populate with just the email if available
        if (window.currentLearner && window.currentLearner.email) {
             populateProfileModal({ email: window.currentLearner.email });
        }
        return;
    }
    const learnerId = window.currentLearner.uid;
    const learnerEmail = window.currentLearner.email; // Get email from auth

    console.log(`Loading profile for UID: ${learnerId}, Email: ${learnerEmail}`); // Add log

    db.collection('learners').doc(learnerId).get()
        .then(doc => {
            if (doc.exists) {
                const learnerData = doc.data();
                console.log("Learner profile data from Firestore:", learnerData);

                // Ensure the email from auth is included if not in Firestore data
                const finalData = {
                    ...learnerData, // Spread existing data
                    email: learnerEmail // Always use the email from auth state
                };

                if (finalData.name) { // Update greeting if name exists in profile
                    window.currentLearner.name = finalData.name;
                    updateGreeting(finalData.name);
                } else {
                    // If no name in profile, use email for greeting
                    updateGreeting(learnerEmail);
                }
                populateProfileModal(finalData); // Populate with combined data

            } else {
                console.log("No learner profile found in Firestore for UID:", learnerId);
                // Populate modal with only the email from auth state
                populateProfileModal({ email: learnerEmail });
                 updateGreeting(learnerEmail); // Use email for greeting initially
            }
        })
        .catch(error => {
            console.error("Error fetching learner profile:", error);
            // Populate modal with only the email from auth state as a fallback
            populateProfileModal({ email: learnerEmail });
            updateGreeting(learnerEmail); // Use email for greeting on error
        });
}

// --- Authentication Listener ---
auth.onAuthStateChanged(user => {
    if (user) {
        console.log("User logged in:", user.uid, "Email:", user.email); // Log email here too
        window.currentLearner = {
            uid: user.uid,
            email: user.email, // Make sure email is captured
            name: user.displayName || user.email // Initial name (can be overwritten by profile)
        };

        // Update greeting immediately with initial info
        updateGreeting(window.currentLearner.name);

        // Load learner-specific data
        loadLearnerProfile(); // Load profile (will populate modal)
        fetchMatchedCourses(); // Fetch matched courses

    } else {
        // User is signed out
        console.log("User logged out or not logged in.");
        // Redirect to login page if not authenticated
        window.location.href = "/signin"; // Adjust redirect as needed
    }
});

// --- Fetch Matched Courses ---
function fetchMatchedCourses() {
    console.log("Fetching matched courses...");
    fetch('/get_matched_courses') // Call the new backend route
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Matched courses received:", data);
            renderMatchedCourses(data.courses || []); // Pass courses array to renderer
        })
        .catch(error => {
            console.error("Error fetching matched courses:", error);
            // Display an error message on the dashboard
            const container = document.getElementById('matched-courses-container');
            if (container) {
                container.innerHTML = `<p class="text-red-500">Could not load matched courses. Please try again later.</p>`;
            }
        });
}

// --- Render Matched Courses ---
function renderMatchedCourses(courses) {
    const container = document.getElementById('matched-courses-container');
    if (!container) {
        console.error("Matched courses container not found in HTML.");
        return;
    }

    container.innerHTML = ''; // Clear previous content

    if (!courses || courses.length === 0) {
        container.innerHTML = '<p class="text-gray-600">No courses matching your skill and time preferences found yet. Complete your profile or check back later!</p>';
        return;
    }

    const grid = document.createElement('div');
    grid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"; // Example grid layout

    courses.forEach(course => {
        const courseCard = document.createElement('div');
        courseCard.className = "bg-white p-4 rounded shadow hover:shadow-lg transition-shadow";

        // Basic YouTube Embed (Helper function needed)
        const videoEmbedHtml = getYoutubeEmbedHtml(course.youtube_link, 200); // Example height 200px

        courseCard.innerHTML = `
            ${videoEmbedHtml}
            <h3 class="text-lg font-semibold mt-2 mb-1 text-green-700">${course.title || 'Untitled Course'}</h3>
            <p class="text-sm text-gray-500 mb-2">By Mentor: ${course.mentor_email || 'N/A'}</p>
            <p class="text-sm text-gray-700 mb-2"><strong>Summary:</strong> ${course.summary ? escapeHtml(course.summary.substring(0, 150)) + '...' : 'Not available'}</p>
            <details class="text-sm">
                <summary class="cursor-pointer text-blue-600 hover:underline">View Learning Content</summary>
                <div class="mt-2 p-2 border rounded bg-gray-50 text-gray-800">${course.learning_content ? formatMarkdown(course.learning_content) : 'Not available'}</div>
            </details>
            <a href="${course.youtube_link || '#'}" target="_blank" rel="noopener noreferrer" class="text-xs text-blue-500 hover:text-blue-700 block mt-2">Watch on YouTube</a>
        `;
        grid.appendChild(courseCard);
    });

    container.appendChild(grid);
}

  // Attempt to find a mentor directly from Firestore (as a fallback)
  function findMentorDirectly(skillInterest, skillLevel, preferredDays, preferredTime) {
      // Query for mentors that match the learner's criteria
      db.collection('mentors')
          .where('skills', 'array-contains', skillInterest)
          .where('skill_level', '>=', skillLevel)
          .get()
          .then(snapshot => {
              if (snapshot.empty) {
                  console.log('No matching mentors found in Firestore.');
                  updateUIWithNoMentorAssigned();
                  return;
              }
              
              // Find best match considering time preferences if possible
              let bestMatch = null;
              snapshot.forEach(doc => {
                  const mentorData = doc.data();
                  // Simple matching logic - can be expanded
                  if (mentorData.availability && 
                      mentorData.availability.includes(preferredDays) && 
                      mentorData.time_slots && 
                      mentorData.time_slots.includes(preferredTime)) {
                      bestMatch = mentorData;
                      bestMatch.id = doc.id;
                      return; // Break on first good match
                  }
                  // Fallback if no perfect time match
                  if (!bestMatch) {
                      bestMatch = mentorData;
                      bestMatch.id = doc.id;
                  }
              });
              
              if (bestMatch) {
                  console.log("Found mentor directly from Firestore:", bestMatch);
                  // Update UI with mentor info
                  const mentorInfoP = document.getElementById('mentor-info');
                  if (mentorInfoP) {
                      mentorInfoP.textContent = bestMatch.name || "Mentor #" + bestMatch.id;
                      mentorInfoP.classList.add('text-green-700');
                      mentorInfoP.classList.remove('text-gray-500');
                  }
                  
                  // Update mentor name label
                  const mentorNameLabel = document.getElementById('mentorNameLabel');
                  if (mentorNameLabel) {
                      mentorNameLabel.textContent = bestMatch.name || "Mentor #" + bestMatch.id;
                  }
                  
                  // Find a relevant course
                  findCourseForMentor(bestMatch.id, skillInterest);
                  
                  // Set session time if available
                  updateSessionInfo(preferredDays, preferredTime);
              } else {
                  updateUIWithNoMentorAssigned();
              }
          })
          .catch(error => {
              console.error("Error finding mentor from Firestore:", error);
              updateUIWithNoMentorAssigned();
          });
  }
  
  // Basic HTML escaping
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Basic Markdown to HTML (needs improvement for full support)
function formatMarkdown(text) {
    if (!text) return '';
    // Simple replacements - consider a library like 'marked' for robust conversion
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Bold
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');       // Italic
    html = html.replace(/^- (.*?)(\n|$)/gm, '<li>$1</li>'); // List items (basic)
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>'); // Wrap lists
    html = html.replace(/\n/g, '<br>'); // Line breaks
    return `<div class="prose prose-sm max-w-none">${html}</div>`; // Basic styling wrapper
}


// Helper to get YouTube Embed HTML
function getYoutubeVideoId(url) {
  if (!url) return null;
  let videoId = null;
  const patterns = [
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)/,
    /(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)/,
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)/,
    /(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^?]+)/
  ];
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      videoId = match[1];
      // Remove potential extra params attached to ID in some formats
      const queryIndex = videoId.indexOf('?');
      if (queryIndex !== -1) videoId = videoId.substring(0, queryIndex);
      const hashIndex = videoId.indexOf('#');
      if (hashIndex !== -1) videoId = videoId.substring(0, hashIndex);
      break;
    }
  }
  return videoId;
}

function getYoutubeEmbedHtml(youtubeUrl, height = 200) {
    const videoId = getYoutubeVideoId(youtubeUrl);
    if (!videoId) {
        return '<p class="text-red-500 text-xs">Invalid YouTube link</p>';
    }
    // Use the privacy-enhanced mode URL
    const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}`;
    // Responsive wrapper (optional but recommended)
    return `
        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000;">
            <iframe
                style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
                src="${embedUrl}"
                title="YouTube video player"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        </div>
    `;
}
  
  // --- Course Details Dialog ---
  function openCourseDialog() {
      if (!assignedCourse) {
          console.log("No assigned course data to display.");
          showMockCourseDialog(); // Use mock data for testing
          return;
      }
      const dialog = document.getElementById('course-details-dialog');
      const courseNameEl = document.getElementById('dialog-course-name');
      const courseDetailsEl = document.getElementById('dialog-course-details');
      const courseLinkEl = document.getElementById('dialog-course-link');
  
      courseNameEl.textContent = assignedCourse.name || assignedCourse.title || "Course Details";
      // Populate details (adjust based on your Firestore course structure)
      let detailsHtml = `<p>${assignedCourse.description || "No description available."}</p>`;
      if (assignedCourse.duration) detailsHtml += `<p class="mt-2"><strong>Duration:</strong> ${assignedCourse.duration}</p>`;
      if (assignedCourse.level) detailsHtml += `<p><strong>Level:</strong> ${assignedCourse.level}</p>`;
      if (assignedCourse.prerequisites) detailsHtml += `<p><strong>Prerequisites:</strong> ${assignedCourse.prerequisites}</p>`;
      // Add more fields like modules, instructor, etc. as needed
  
      courseDetailsEl.innerHTML = detailsHtml;
  
      // Optional: Update link if course.html needs a specific course ID
      if (assignedCourse.id) {
           courseLinkEl.href = `/course.html?id=${assignedCourse.id}`; // Example: Pass ID as query param
      } else {
           courseLinkEl.href = '/course.html'; // Default link
      }
  
      dialog.classList.remove('hidden');
  }
    
  window.openProfileModal = function() { // Make globally accessible for onclick
      const modal = document.getElementById('learnerProfileModal');
      if (modal) modal.classList.remove('hidden');
  }
  
  window.closeProfileModal = function() { // Make globally accessible for onclick
      const modal = document.getElementById('learnerProfileModal');
      if (modal) modal.classList.add('hidden');
  }
  
// --- Save Learner Profile ---
window.saveLearnerProfile = function(event) {
    if (event) event.preventDefault(); // Prevent form submission

    // Get email from the disabled field OR from the global variable as fallback
    const email = document.getElementById("learnerEmail").value || window.currentLearner?.email;

    const profileData = {
        name: document.getElementById("learnerName").value,
        // email: email, // *** Don't send email back, it shouldn't be changed ***
        age: document.getElementById("learnerAge").value,
        gender: document.getElementById("learnerGender").value,
        skillinterest: document.getElementById("skillinterest").value,
        skilllevel: document.getElementById("skilllevel").value,
        preferreddays: document.getElementById("preferreddays").value,
        preferredtime: document.getElementById("preferredtime").value,
        goals: document.getElementById("learnerGoals").value
    };

    // Make sure we have a UID to save against
    if (!window.currentLearner || !window.currentLearner.uid) {
         showNotification("Error: Not logged in properly. Cannot save profile.", true);
         console.error("Cannot save profile, currentLearner or UID missing.");
         return;
    }

    console.log("Saving profile data:", profileData, "for UID:", window.currentLearner.uid);

    // Call the backend update route
    fetch('/update_learner_profile', { // Use the UPDATE route
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData) // Send data *without* email
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || `Server error: ${response.status}`) });
        }
        return response.json();
    })
    .then(result => {
        console.log("Profile save API result:", result);
        showNotification(result.message || "Profile saved successfully!");
        closeProfileModal();

        // Update global state and greeting immediately after successful save
        if (profileData.name) {
            window.currentLearner.name = profileData.name;
            updateGreeting(profileData.name);
        }
        // Optionally refetch matched courses if profile change might affect matches
        fetchMatchedCourses();
    })
    .catch(err => {
        console.error("Profile save API error:", err);
        showNotification(`Error saving profile: ${err.message}`, true);
    });
};

// --- ADD this function if it doesn't exist ---
// (Or modify if you already have a different updateUIWithNoMentorAssigned)
function updateUIWithNoMentorAssigned() {
    console.log("UI Updated: No mentor assigned.");
    // Example: Clear mentor info sections if they exist
    const mentorInfoP = document.getElementById('mentor-info');
    if (mentorInfoP) {
        mentorInfoP.textContent = "Not Assigned Yet";
        mentorInfoP.classList.remove('text-green-700');
        mentorInfoP.classList.add('text-gray-500');
    }
    const mentorNameLabel = document.getElementById('mentorNameLabel');
     if (mentorNameLabel) {
        mentorNameLabel.textContent = "N/A";
    }
    // Clear session info too
    updateSessionInfo(null, null);
}

// --- ADD this function if it doesn't exist ---
// (Or modify if you already have a different updateSessionInfo)
function updateSessionInfo(day, time) {
    console.log(`UI Updated: Session Info - Day: ${day}, Time: ${time}`);
    // Example: Update elements showing session time
    const sessionTimeElement = document.getElementById('session-time-info'); // Assuming you have an element with this ID
    if (sessionTimeElement) {
        if (day && time) {
            sessionTimeElement.textContent = `Scheduled: ${day}, ${time}`;
            sessionTimeElement.classList.add('text-blue-700');
             sessionTimeElement.classList.remove('text-gray-500');
        } else {
            sessionTimeElement.textContent = "Not Scheduled";
            sessionTimeElement.classList.remove('text-blue-700');
            sessionTimeElement.classList.add('text-gray-500');
        }
    }
}

  // --- DOMContentLoaded (Ensure new fetch is called) ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed for learner.");
    // Profile form setup (keep existing)
    const profileForm = document.getElementById('learnerProfileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', saveLearnerProfile); // Use correct function name
    } else {
        console.warn("Learner profile form not found.");
    }
    // No need to attach listener for course dialog trigger if it's removed/replaced
    console.log("Learner event listeners attached.");
    // Initial data fetch happens in onAuthStateChanged
});
  
  function showNotification(message, isError = false) {
    // Keep your existing logic
    const notification = document.getElementById('notification');
    if (!notification) return;
    notification.textContent = message;
    notification.classList.remove('translate-y-20', 'opacity-0', 'bg-green-600', 'bg-red-600');
    if (isError) {
        notification.classList.add('bg-red-600');
    } else {
        notification.classList.add('bg-green-600');
    }
    notification.classList.add('translate-y-0', 'opacity-100');
    setTimeout(() => {
        notification.classList.remove('translate-y-0', 'opacity-100');
        notification.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

  window.logout = function() { // Make globally accessible for onclick
      auth.signOut().then(() => {
          console.log("User signed out successfully.");
          window.location.href = "/signin"; // Redirect after logout
      }).catch((error) => {
          console.error("Sign out error:", error);
          showNotification("Error logging out.", true);
      });
  }