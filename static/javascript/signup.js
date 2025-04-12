// Initialize Firebase using the injected config
let firebaseConfigFromServer = null;
try {
    firebaseConfigFromServer = JSON.parse(window.firebaseConfigFromServer);
} catch (e) {
    console.error("Error parsing Firebase config:", e);
}

if (firebaseConfigFromServer) { // Check if config was successfully parsed
   const app = initializeApp(firebaseConfigFromServer);
   const analytics = getAnalytics(app); // Initialize other services as needed
   const auth = getAuth(app);
   console.log("Firebase initialized from server config.");
   // ... rest of your JS code that uses auth, db, etc.
} else {
     console.error("Firebase config not provided or invalid.");
     // Handle the error - maybe disable Firebase-dependent features
}
  
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