# Pipe Network Bot



## 💻 Requirements

- Python >=3.10<=3.11
- Internet connection
- Valid email accounts for registration
- Valid proxies

---

## 🛠️ Setup

1. Clone the repository:
   ```bash
   git clone [repository URL]
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   cd venv/Scripts
   activate
   cd ../..
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---
### Other Configuration Files

#### 📁 register.txt
Contains accounts for registration.
```
Format:
email:password
email:password
...
```

#### 📁 farm.txt
Contains accounts for farming and task completion.
```
Format:
email:password
email:password
...
```

#### 📁 proxies.txt
Contains proxy information.
```
Format:
http://user:pass@ip:port
http://ip:port:user:pass
http://ip:port@user:pass
http://user:pass:ip:port
...
```

---

## 🚀 Usage

1. Ensure all configuration files are set up correctly.
2. Run the bot:
   ```bash
   python run.py
   ```

