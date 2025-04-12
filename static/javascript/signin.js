// Import necessary Firebase SDK functions
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-analytics.js";
import { getAuth, signInWithEmailAndPassword, sendPasswordResetEmail } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js";
import { getIdTokenResult } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js";

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
const analytics = getAnalytics(app);
const auth = getAuth(app);

const submitSignIn = document.getElementById('submitsignin');
const resetPasswordButton = document.getElementById('reset-password-btn');
const resetPasswordContainer = document.getElementById('reset-password-container');
const resetEmailInput = document.getElementById('reset-email');
const signInEmailInput = document.getElementById('email');

submitSignIn.addEventListener("click", function (event) {
  event.preventDefault();

  const email = signInEmailInput.value;
  const password = document.getElementById('password').value;

signInWithEmailAndPassword(auth, email, password)
  .then((userCredential) => {
    const user = userCredential.user;
    alert("Successfully signed in...");
    return user.getIdTokenResult();
  })
  .then((idTokenResult) => {
    const role = idTokenResult.claims.role || "user";
    console.log("Custom Role:", role);

    // Send token to Flask to create session
    return fetch('/sessionLogin', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ idToken: idTokenResult.token })
    })
    .then((res) => {
      if (!res.ok) throw new Error("Session login failed");
      return role;
    });
  })

  .then((role) => {
    if (role === "admin") {
      window.location.href = "/admin_dashboard";
    } else if (role === "mentor") {
      window.location.href = "/mentor_dashboard";
    } else if (role === "learner") {
      window.location.href = "/learner_dashboard";
    } else {
      window.location.href = "/upload"; // fallback
    }
    
  
  })
  .catch((error) => {
    const errorCode = error.code || "";
    const errorMessage = error.message || "Unknown error";
    alert(`Error: ${errorMessage}`);
    console.log("Error during sign in:", errorCode, errorMessage);
  });
});
resetPasswordButton.addEventListener('click', function () {
  const enteredEmail = signInEmailInput.value;

  if (enteredEmail) {
    resetEmailInput.value = enteredEmail;
    resetPasswordContainer.style.display = 'block';

    sendPasswordResetEmail(auth, enteredEmail)
      .then(() => {
        alert("Password reset email sent! Please check your inbox.");
        resetPasswordContainer.style.display = 'none'; 
      })
      .catch((error) => {
        const errorCode = error.code;
        const errorMessage = error.message;
        alert(`Error: ${errorMessage}`); 
        console.log("Error during password reset:", errorCode, errorMessage);
      });
  } else {
    alert("Please enter your email first.");
  }
});