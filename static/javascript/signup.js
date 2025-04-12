  // Import the functions you need from the SDKs you need
  import { initializeApp } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-app.js";
  import { getAnalytics } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-analytics.js";
  import { getAuth, createUserWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/11.4.0/firebase-auth.js";

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
  
  const submitsignup= document.getElementById('submitsignup');

  submitsignup.addEventListener("click", function(event){
      event.preventDefault()

      const fullname= document.getElementById('fullname').value;
      const email= document.getElementById('email').value;
      const password= document.getElementById('password').value;
      const selectedRole = document.querySelector('input[name="role"]:checked')?.value;

      if (!selectedRole) {
        alert("Please select a role (Mentor or Learner).");
        return;
      }

     createUserWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
      const user = userCredential.user;
      alert("Creating account...");

      return user.getIdToken(); // Get Firebase ID token
    })
    .then((idToken) => {
      // Send role and token to Flask to set custom claims
      return fetch('/setCustomClaims', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          idToken: idToken,
          role: selectedRole
        })
      });
    })
    .then((res) => {
      if (!res.ok) throw new Error("Failed to set custom claims");
      window.location.href = "/signin";
    })
    .catch((error) => {
      alert(error.message);
      console.log("Signup Error:", error);
    });
});