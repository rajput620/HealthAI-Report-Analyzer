console.log("login.js loaded");


// ================= FIREBASE CONFIG =================

const firebaseConfig = {
  apiKey: "AIzaSyBqkMcOkj8v2_9pKEJB35YivVeyoJ7brwQ",
  authDomain: "healthai-25824.firebaseapp.com",
  projectId: "healthai-25824",
  storageBucket: "healthai-25824.firebasestorage.app",
  messagingSenderId: "404563155530",
  appId: "1:404563155530:web:c5ff86bce4ce019ce5a4b3"
};

// INIT FIREBASE
firebase.initializeApp(firebaseConfig);


// ================= LOGIN =================

function loginUser() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    fetch('/login-user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(res => res.json())
    .then(data => {
        console.log(data);

        if (data.success) {
            // 🔥 FIXED (break iframe)
            window.top.location.href = "/dashboard";
        } else {
            alert(data.message);
        }
    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}


// ================= PASSWORD TOGGLE =================

function togglePassword() {
    const pass = document.getElementById("password");
    pass.type = pass.type === "password" ? "text" : "password";
}


// ================= GOOGLE LOGIN =================

function googleLogin(){

    const provider = new firebase.auth.GoogleAuthProvider();

    firebase.auth().signInWithPopup(provider)
    .then(result => {

        const email = result.user.email;

        console.log("Google user:", email);

        // SEND TO BACKEND
        fetch('/google-login', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({email})
        })
        .then(res => res.json())
        .then(data => {
            if(data.success){

                // 🔥 FIXED
                window.top.location.href = "/dashboard";
            }
        });

    })
    .catch(err => {
        console.error(err);
        alert(err.message);
    });
}




const quotes = [
    "Artificial Intelligence is reshaping healthcare by shifting focus from treatment to prevention. It enables early detection and smarter decisions that can save lives.",

    "Healthcare powered by AI is no longer about reacting to illness. It is about predicting risks and taking action before problems even begin.",

    "Your health data holds valuable insights about your future well-being. AI transforms this data into clear guidance that helps you live a healthier life.",

    "Modern healthcare is evolving beyond traditional methods. With AI, diagnosis becomes faster, more accurate, and deeply personalized.",

    "The future of medicine lies in intelligent systems that understand patterns humans might miss. AI brings clarity to complex health conditions.",

    "Preventive care is becoming the foundation of a healthier world. AI empowers individuals to act early and avoid serious medical issues.",

    "Every heartbeat, every habit, and every symptom tells a story. AI connects these signals to provide meaningful and actionable health insights.",

    "Healthcare decisions should not rely on guesswork anymore. AI ensures that every recommendation is backed by data and precision.",

    "Technology and healthcare are merging to create a smarter ecosystem. AI enables faster analysis and better outcomes for every individual.",

    "Understanding your health should not be complicated. AI simplifies complex medical data into clear insights you can trust and act upon."
];

function showRandomQuote() {
    const quoteElement = document.getElementById("aiQuote");
    const randomIndex = Math.floor(Math.random() * quotes.length);
    quoteElement.innerText = quotes[randomIndex];
}

window.onload = showRandomQuote;