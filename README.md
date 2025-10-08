# 🔮 ManMitra — AI & Support Microservice (`fast_api2/`)

## 📖 Overview
**ManMitra FastAPI Microservice** is the intelligent engine behind the ManMitra Student Web Portal. It powers:

- The **Bestie Chatbot** for mental health first-aid  
- **Content safety checks** to ensure messages are appropriate  
- **Counselor and admin insights** to track student well-being  

It works quietly in the background, analyzing messages, flagging risks, and alerting counselors if a student needs urgent support.

---

## 🚀 Key Features

### 💬 Bestie Chatbot
- Provides **confidential, AI-driven support** for students  
- Responds to students’ worries, stress, or anxiety  

### 🛡️ Safety & Moderation
- Automatically checks messages for unsafe content  
- Ensures students’ messages are **private, safe, and respectful**  

### 📊 Analytics & Insights
- Summarizes anonymized data to help counselors understand student well-being trends  
- Tracks engagement and progress without storing personal details  

### 🔔 Escalation System
- If a student shows **high-risk behavior**, counselors and admins are notified immediately  
- Provides a **structured alert** while maintaining privacy  

---

## 🧩 How It Works (Simple Version)
1. **Student sends a message** to Bestie via the web portal.  
2. **Microservice checks the message** for safety (self-harm, sensitive info, etc.).  
3. **AI generates a response** if the message is safe.  
4. **High-risk messages** trigger an alert to a counselor/admin.  
5. **Insights** are anonymously tracked to improve student support.  

> Think of it as a **smart, friendly companion** that talks to students safely and ensures counselors are notified if help is needed.

---

## ⚡ Benefits

- **Safe & supportive:** All messages are moderated for safety  
- **Confidential:** Students can share feelings anonymously  
- **Helpful:** Provides AI-guided first-aid support  
- **Insightful:** Gives counselors anonymous data to improve support  

---

## 🚀 Getting Started (For Demo / Development)
- The service can run **locally or via Docker**  
- Open the **documentation page** at `/docs` to see how the chatbot and moderation system works  
- Alerts and notifications are sent **securely and automatically** if a student is at risk  

---

## 🔒 Privacy & Ethics
- **Anonymous by default:** Students do not need to share personal info  
- **No diagnosis:** AI only gives first-aid support  
- **Safe escalation:** High-risk alerts go only to trained counselors  
- **Ethical design:** Clinical guidelines reviewed by licensed mental health professionals  

---

## 🌟 Summary
This microservice is the **brains behind ManMitra** — it keeps the chatbot smart, safe, and responsive, while ensuring students receive support in a **confidential and caring way**.  

Think of it as the **silent guardian and intelligent friend** in the background of the student portal.  
