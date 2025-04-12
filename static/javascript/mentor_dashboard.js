import { initializeApp } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyCj4PgVbGNf1faHSwXekGj4Hg2FHNuAdvo",
  authDomain: "craftecho.firebaseapp.com",
  projectId: "craftecho",
  storageBucket: "craftecho.firebasestorage.app",
  messagingSenderId: "859530568811",
  appId: "1:859530568811:web:9b64c5283357d2b1bb7d2e",
  measurementId: "G-ED411QMMBY"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

let currentMentor = null;
let entryCounter = 0;

document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM fully loaded and parsed for mentor.");
  // Existing profile button listener
  const openProfileBtn = document.getElementById("completeProfileBtn");
  if (openProfileBtn) {
      openProfileBtn.onclick = () => {
          // Keep existing profile fetch and modal opening logic
          document.getElementById("profileModal").classList.remove("hidden");
          fetch("/get_mentor_profile")
              .then(res => {
                  if (!res.ok) throw new Error(`Failed to fetch profile (${res.status})`);
                  return res.json();
               })
              .then(data => {
                  currentMentor = data; // Store fetched profile data
                  // Keep existing code to populate profile form fields
                  if (data.name) document.getElementById("mentorName").value = data.name;
                  if (data.email) document.getElementById("mentorEmail").value = data.email;
                  // ... populate other fields ...
                  if (data.age) document.getElementById("mentorAge").value = data.age;
                  if (data.gender) document.getElementById("mentorGender").value = data.gender;
                  if (data.primaryskill) document.getElementById("mentorPrimarySkill").value = data.primaryskill;
                  if (data.experience) document.getElementById("mentorExperience").value = data.experience;
                  if (data.bio) document.getElementById("mentorBio").value = data.bio;
                  if (data.availableTime) document.getElementById("mentorAvailableTime").value = data.availableTime;
                  if (data.availableDay) document.getElementById("mentorAvailableDay").value = data.availableDay;
              })
              .catch(err => {
                  console.error("Fetch mentor profile failed:", err);
                  alert(`Error loading profile: ${err.message}`);
              });
      };
  }
  const profileForm = document.getElementById("profileForm");
  if (profileForm) {
      profileForm.addEventListener("submit", function(e) {
          e.preventDefault();
          saveProfile(); // Assumes saveProfile function exists (keep it)
      });
  }
  const addMoreBtn = document.getElementById("addMore");
  if (addMoreBtn) {
      addMoreBtn.addEventListener("click", () => addCourseEntry(false)); // Add non-first entry
  }

  const courseForm = document.getElementById("courseForm");
  if (courseForm) {
      courseForm.addEventListener("submit", function(e) {
          e.preventDefault();
          submitCourses(); // Assumes submitCourses function exists (keep it)
      });
  }

  // Add only one initial course entry when the page loads
  if (document.getElementById('courseContainer') && document.querySelectorAll('.course-entry').length === 0) {
      addCourseEntry(true); // true indicates this is the first entry
  }
  fetchMyCourses();

  auth.onAuthStateChanged(user => {
      if (user) {
          currentMentor = { // Store basic info immediately
              uid: user.uid,
              email: user.email
          };
          // Populate email field in the initial course entry if needed
          const firstEmailInput = document.querySelector('#courseContainer input[name="mentor_email"]');
          if (firstEmailInput && !firstEmailInput.value) {
              firstEmailInput.value = user.email;
          }
      } else {
          alert("Please log in to access the mentor dashboard");
          window.location.href = "/signin";
      }
  });
});

// --- NEW: Fetch Mentor's Own Courses ---
function fetchMyCourses() {
  console.log("Fetching mentor's submitted courses...");
  fetch('/get_my_courses') // Call the new backend route
      .then(response => {
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then(data => {
          console.log("Mentor's courses received:", data);
          renderMyCourses(data.courses || []); // Pass courses array to renderer
      })
      .catch(error => {
          console.error("Error fetching mentor's courses:", error);
          const container = document.getElementById('my-courses-container');
          if (container) {
              container.innerHTML = `<p class="text-red-500">Could not load your submitted courses. Please try refreshing.</p>`;
          }
      });
}

// --- NEW: Render Mentor's Own Courses ---
function renderMyCourses(courses) {
  const container = document.getElementById('my-courses-container');
  if (!container) {
      console.error("Container 'my-courses-container' not found in HTML.");
      return;
  }

  container.innerHTML = ''; // Clear previous content

  if (!courses || courses.length === 0) {
      container.innerHTML = '<p class="text-gray-600 italic">You haven\'t submitted any courses yet. Use the form above to add your first module!</p>';
      return;
  }

  const list = document.createElement('ul');
  list.className = "space-y-3"; // Example styling

  courses.forEach(course => {
      const listItem = document.createElement('li');
      listItem.className = "bg-white p-3 border border-gray-200 rounded shadow-sm";
      // Display basic course info
      listItem.innerHTML = `
          <h4 class="font-medium text-indigo-800">${course.title || 'Untitled Course'}</h4>
          <p class="text-xs text-gray-500">Submitted: ${course.created_at_iso ? new Date(course.created_at_iso).toLocaleDateString() : 'N/A'}</p>
          <p class="text-sm mt-1">Link: <a href="${course.youtube_link || '#'}" target="_blank" class="text-blue-600 hover:underline">${course.youtube_link ? course.youtube_link.substring(0, 40) + '...' : 'N/A'}</a></p>
          <details class="text-xs mt-1">
              <summary class="cursor-pointer text-gray-600 hover:text-gray-800">Show Processed Content</summary>
              <div class="mt-1 p-2 bg-gray-50 rounded border">
                  <p><strong>Summary:</strong> ${course.summary || '[Not Processed]'}</p>
                  <p class="mt-1"><strong>Learning Content:</strong> ${course.learning_content || '[Not Processed]'}</p>
              </div>
          </details>
          `;
      list.appendChild(listItem);
  });

  container.appendChild(list);
}

window.closeModal = function () {
  document.getElementById("profileModal").classList.add("hidden");
};

function createSpinnerHTML() {
  return `<span class="inline-flex items-center"><span class="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-2"></span>Processing...</span>`;
}

function addCourseEntry(isFirst = false) {
  entryCounter++;
  const container = document.getElementById('courseContainer');
  const entry = document.createElement('div');
  entry.className = 'course-entry bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6';
  entry.dataset.entryId = entryCounter;

  // Main form content remains the same
  entry.innerHTML = `
    <div class="mb-4">
      <label class="block text-gray-700 text-sm font-bold mb-2">Mentor Email:</label>
      <input type="email" name="mentor_email" placeholder="Enter your email" required
        class="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-indigo-500"
        value="${currentMentor?.email || ''}">
    </div>

    <div class="mb-4">
      <label class="block text-gray-700 text-sm font-bold mb-2">YouTube Video Link:</label>
      <div class="flex items-center">
        <input type="text" name="youtube_link" placeholder="Enter video link" required
          class="flex-1 border rounded px-3 py-2 focus:outline-none focus:ring focus:border-indigo-500 mr-2">
        <button type="button" class="process-btn px-4 py-2 rounded bg-indigo-500 text-white hover:bg-indigo-600">
          Process Content
        </button>
        <span class="processing-indicator hidden ml-2 text-amber-500"></span>
        <span class="processed-success hidden ml-2 text-green-500">✔ Processed!</span>
      </div>
    </div>

    <div class="mb-4">
      <label class="block text-gray-700 text-sm font-bold mb-2">Course Title:</label>
      <input type="text" name="title" placeholder="Enter course title" required
        class="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-indigo-500">
    </div>

    <div class="mb-4">
      <label class="block text-gray-700 text-sm font-bold mb-2">Mentor Description:</label>
      <textarea name="additional_info" rows="4" placeholder="Enter description"
        class="w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-indigo-500"></textarea>
    </div>

    <div class="hidden-data hidden">
      <input type="hidden" name="summary" value="">
      <input type="hidden" name="transcript" value="">
      <input type="hidden" name="learning_content" value="">
      <input type="hidden" name="processed" value="false">
    </div>
    
    ${!isFirst ? `
    <div class="flex justify-end mt-2">
      <button type="button" class="remove-entry-btn px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600">
        Remove Lesson
      </button>
    </div>
    ` : ''}
  `;

  container.appendChild(entry);
  
  // Add event listener to the remove button if this isn't the first entry
  if (!isFirst) {
    const removeButton = entry.querySelector('.remove-entry-btn');
    if (removeButton) {
      removeButton.addEventListener('click', () => entry.remove());
    }
  }
  
  attachProcessListener(entry.querySelector('.process-btn'));
}
function attachProcessListener(button) {
  button.addEventListener('click', function () {
    handleProcessClick(this);
  });
}

function handleProcessClick(button) {
  const entryDiv = button.closest('.course-entry');
  const youtubeLinkInput = entryDiv.querySelector('input[name="youtube_link"]');
  const processingIndicator = entryDiv.querySelector('.processing-indicator');
  const successIndicator = entryDiv.querySelector('.processed-success');
  const hiddenProcessedFlag = entryDiv.querySelector('input[name="processed"]');
  const hiddenSummary = entryDiv.querySelector('input[name="summary"]');
  const hiddenTranscript = entryDiv.querySelector('input[name="transcript"]');
  const hiddenLearningContent = entryDiv.querySelector('input[name="learning_content"]');

  const youtubeLink = youtubeLinkInput.value.trim();
  if (!youtubeLink) {
    alert("Please enter a YouTube link first.");
    return;
  }

  button.disabled = true;
  button.textContent = 'Processing...';
  processingIndicator.classList.remove('hidden');
  processingIndicator.innerHTML = createSpinnerHTML();
  successIndicator.classList.add('hidden');
  hiddenProcessedFlag.value = 'false';

  fetch('/process_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_link: youtubeLink })
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(err => { throw new Error(err.error || "Processing failed"); });
    }
    return response.json();
  })
  .then(data => {
    hiddenSummary.value = data.summary || '';
    hiddenTranscript.value = data.transcription || '';
    hiddenLearningContent.value = data.learning_content || '';
    hiddenProcessedFlag.value = 'true';

    processingIndicator.classList.add('hidden');
    successIndicator.classList.remove('hidden');
    button.textContent = 'Reprocess';
  })
  .catch(error => {
    console.error('Processing Error:', error);
    alert(`Processing failed: ${error.message}`);
    processingIndicator.classList.add('hidden');
    button.textContent = 'Process Content';
  })
  .finally(() => {
    button.disabled = false;
  });
}

function submitCourses() {
  const courseForm = document.getElementById('courseForm');
  const submitButton = courseForm.querySelector('button[type="submit"]');
  const entries = document.querySelectorAll('#courseContainer .course-entry');
  const coursesPayload = [];
  let allProcessed = true;

  submitButton.disabled = true;
  submitButton.textContent = 'Submitting...';

  document.getElementById('submitError').classList.add('hidden');

  entries.forEach((entry, index) => {
    const processedFlag = entry.querySelector('input[name="processed"]').value === 'true';
    const titleInput = entry.querySelector('input[name="title"]');
    const youtubeLinkInput = entry.querySelector('input[name="youtube_link"]');

    // Check if essential fields are filled and content is processed
    if (!processedFlag || !titleInput.value || !youtubeLinkInput.value) {
        allProcessed = false;
        // Highlight the entry with the issue (optional)
        entry.style.borderColor = 'red';
        console.warn(`Entry ${index + 1} is not fully processed or filled.`);
    } else {
        entry.style.borderColor = ''; // Reset border if previously marked
    }

    // Collect data regardless of processing state for backend submission
    coursesPayload.push({
      mentor_email: entry.querySelector('input[name="mentor_email"]').value,
      youtube_link: youtubeLinkInput.value,
      title: titleInput.value,
      additional_info: entry.querySelector('textarea[name="additional_info"]').value,
      // Get values from hidden fields
      summary: entry.querySelector('input[name="summary"]').value,
      transcript: entry.querySelector('input[name="transcript"]').value,
      learning_content: entry.querySelector('input[name="learning_content"]').value,
    });
  });

  if (!allProcessed) {
    document.getElementById('submitError').classList.remove('hidden');
    document.getElementById('submitError').textContent = 'Please ensure all lessons have a title, YouTube link, and have been successfully processed before publishing.';
    // Re-enable submit button on validation failure
    submitButton.disabled = false;
    submitButton.textContent = 'Publish Course';
    return; // Stop submission
  }

  console.log("Submitting courses:", coursesPayload);

  // Send data to backend
  fetch('/add_courses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ courses: coursesPayload }) // Send as a list under 'courses' key
  })
  .then(res => {
      if (!res.ok) {
          // Try to parse error message from backend
          return res.json().then(err => { throw new Error(err.message || err.error || `Submission failed with status ${res.status}`) });
      }
      return res.json();
   })
  .then(data => {
    console.log("Submission response:", data);
    alert(data.message || "Course(s) submitted successfully!");
    // Clear the form container and add a fresh initial entry
    const container = document.getElementById('courseContainer');
    if (container) container.innerHTML = '';
    entryCounter = 0; // Reset counter
    addCourseEntry(true); // Add the first entry back
    // --- NEW: Refresh the mentor's course list ---
    fetchMyCourses();
    // --- END NEW ---
  })
  .catch(err => {
    console.error('Course Submit Error:', err);
    alert(`Submission failed: ${err.message}`);
    document.getElementById('submitError').textContent = `Submission Error: ${err.message}`;
    document.getElementById('submitError').classList.remove('hidden');
  })
  .finally(() => {
      // Re-enable submit button after API call finishes
      submitButton.disabled = false;
      submitButton.textContent = 'Publish Course';
  });
}



window.saveProfile = async function() {
  if (!currentMentor || !currentMentor.uid) {
    alert("Please log in again to save your profile.");
    return;
  }

  const name = document.getElementById("mentorName").value.trim();
  const email = document.getElementById("mentorEmail").value.trim();
  const age = document.getElementById("mentorAge").value.trim();
  const gender = document.getElementById("mentorGender").value.trim();
  const primaryskill = document.getElementById("mentorPrimarySkill").value.trim();
  const experience = document.getElementById("mentorExperience").value.trim();
  const bio = document.getElementById("mentorBio").value.trim();
  const availableDay = document.getElementById("mentorAvailableDay").value;
  const availableTime = document.getElementById("mentorAvailableTime").value;

  if (!name || !email) {
    alert("Name and email are required.");
    return;
  }

  try {
    const mentorData = {
      uid: currentMentor.uid,
      name,
      email,
      age,
      gender,
      primaryskill,
      experience,
      bio,
      availableTime,
      availableDay,
      updatedAt: new Date().toISOString()
    };

    fetch('/update_mentor_profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(mentorData)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        alert("Profile saved successfully!");
        closeModal();
      } else {
        alert("Error saving profile: " + (data.error || "Unknown error"));
      }
    })
    .catch(error => {
      console.error("Error saving profile:", error);
      alert("Error saving profile: " + error.message);
    });
  } catch (error) {
    console.error("Error saving profile:", error);
    alert("Error saving profile: " + error.message);
  }
};