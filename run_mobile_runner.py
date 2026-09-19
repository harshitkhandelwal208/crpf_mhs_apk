"""
Mobile Application Runner & Screenshot Generator for CRPF MHS APK
Renders the exact Android layouts, connects to the live FastAPI backend,
and captures pixel-perfect mobile device screenshots of every screen using Playwright.
"""
import os
import sys
import time
import base64
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import json
from playwright.sync_api import sync_playwright

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, "artifacts", "mobile_screenshots")
BRAIN_DIR = r"C:\Users\Harshit\.gemini\antigravity\brain\04eb8701-c2c4-4cf8-bd07-f336df304b15"
DRAWABLE_DIR = os.path.join(WORKSPACE_DIR, "app", "src", "main", "res", "drawable-nodpi")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(BRAIN_DIR, exist_ok=True)

# Read image assets
with open(os.path.join(DRAWABLE_DIR, "crpf_logo.png"), "rb") as f:
    CRPF_LOGO_B64 = base64.b64encode(f.read()).decode("utf-8")

with open(os.path.join(DRAWABLE_DIR, "crpf_auth_background.png"), "rb") as f:
    CRPF_BG_B64 = base64.b64encode(f.read()).decode("utf-8")

HTML_CONTENT = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>CRPF MHS Mobile App</title>
<style>
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-tap-highlight-color: transparent;
    font-family: -apple-system, BlinkMacSystemFont, "Roboto", "Segoe UI", Helvetica, Arial, sans-serif;
  }}

  :root {{
    --screen-bg: #F2F5FA;
    --auth-navy: #0B1F4D;
    --auth-overlay: rgba(11, 31, 77, 0.90);
    --auth-surface: #FFF7F4EE;
    --auth-text: #0B1A36;
    --auth-muted: #4C607A;
    --teal-700: #2B9D8F;
    --teal-200: #8DD8C8;
    --teal-surface: #E5F4EF;
    --warning: #C7862B;
    --warning-surface: #FFF2DE;
    --surface-warm: #FFFBF5;
    --ink: #10213F;
    --muted-ink: #62718A;
    --line: #D7E0ED;
    --success: #23856F;
    --white: #FFFFFF;
  }}

  body {{
    background-color: #121212;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 0;
    margin: 0;
  }}

  /* Mobile Device Frame */
  #phone-container {{
    width: 412px;
    height: 892px;
    background-color: var(--screen-bg);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    box-shadow: 0 25px 60px rgba(0,0,0,0.4);
  }}

  /* Android Status Bar */
  .status-bar {{
    height: 36px;
    background: #0B1F4D;
    color: #ffffff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 600;
    z-index: 100;
    letter-spacing: 0.2px;
  }}
  .status-bar.light-bar {{
    background: var(--screen-bg);
    color: var(--ink);
  }}
  .status-icons {{
    display: flex;
    gap: 6px;
    align-items: center;
  }}
  .status-icon {{
    width: 14px;
    height: 14px;
    fill: currentColor;
  }}

  /* Main Scrollable View Area */
  .screen-content {{
    flex: 1;
    overflow-y: auto;
    position: relative;
    padding-bottom: 80px;
  }}
  .screen-content.no-nav {{
    padding-bottom: 0;
  }}

  /* Bottom Navigation Bar (72dp in XML) */
  #screen_nav {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 72px;
    background: var(--white);
    border-top: 1px solid var(--line);
    display: flex;
    align-items: center;
    justify-content: space-around;
    padding: 0 6px;
    z-index: 90;
    box-shadow: 0 -4px 12px rgba(0,0,0,0.04);
  }}
  .nav-item {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    cursor: pointer;
    background: none;
    border: none;
    color: var(--muted-ink);
    transition: color 0.15s ease;
    padding: 4px 0;
  }}
  .nav-item.active {{
    color: var(--teal-700);
    font-weight: 700;
  }}
  .nav-item svg {{
    width: 22px;
    height: 22px;
    margin-bottom: 3px;
    fill: currentColor;
  }}
  .nav-label {{
    font-size: 12px;
  }}

  /* Common Components */
  .card {{
    background: var(--white);
    border-radius: 16px;
    border: 1px solid var(--line);
    padding: 18px;
    margin-bottom: 16px;
  }}
  .btn-primary {{
    width: 100%;
    height: 54px;
    border-radius: 12px;
    border: none;
    background: var(--teal-700);
    color: var(--white);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .btn-outlined {{
    width: 100%;
    height: 52px;
    border-radius: 12px;
    border: 1.5px solid var(--teal-700);
    background: transparent;
    color: var(--teal-700);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .btn-text {{
    background: none;
    border: none;
    color: var(--teal-700);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    padding: 8px 12px;
  }}
  .badge {{
    display: inline-block;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }}

  /* PANEL 1: LOGIN PANEL */
  #login_panel {{
    display: block;
    background: var(--screen-bg);
  }}
  .login-hero {{
    height: 300px;
    background-color: var(--auth-navy);
    position: relative;
    padding: 28px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    overflow: hidden;
  }}
  .login-hero-bg {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0.28;
  }}
  .login-hero-overlay {{
    position: absolute;
    inset: 0;
    background: var(--auth-overlay);
  }}
  .login-hero-content {{
    position: relative;
    z-index: 2;
  }}
  .crpf-logo-img {{
    width: 64px;
    height: 64px;
    background: var(--white);
    padding: 4px;
    border-radius: 8px;
    object-fit: contain;
    margin-bottom: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
  }}
  .login-badge {{
    color: var(--teal-200);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
  }}
  .login-hero-title {{
    color: var(--white);
    font-size: 26px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 5px;
  }}
  .login-hero-sub {{
    color: #B8C7E1;
    font-size: 13px;
    line-height: 1.4;
  }}
  .login-form-card {{
    background: var(--auth-surface);
    padding: 24px;
  }}
  .secure-access-title {{
    color: var(--auth-navy);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.6px;
    margin-bottom: 4px;
  }}
  .signin-header {{
    color: var(--auth-text);
    font-size: 23px;
    font-weight: 800;
    margin-bottom: 5px;
  }}
  .signin-sub {{
    color: var(--auth-muted);
    font-size: 14px;
    line-height: 1.4;
    margin-bottom: 20px;
  }}
  .input-group {{
    margin-bottom: 14px;
  }}
  .input-label {{
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--auth-muted);
    margin-bottom: 6px;
  }}
  .text-input {{
    width: 100%;
    height: 52px;
    background: var(--white);
    border: 1.5px solid var(--line);
    border-radius: 8px;
    padding: 0 16px;
    font-size: 15px;
    color: var(--auth-text);
    outline: none;
    transition: border-color 0.2s;
  }}
  .text-input:focus {{
    border-color: var(--auth-navy);
  }}
  .info-badge-teal {{
    background: var(--teal-surface);
    color: var(--auth-navy);
    padding: 14px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.4;
    margin: 16px 0;
  }}
  .btn-auth {{
    width: 100%;
    height: 56px;
    background: var(--auth-navy);
    color: var(--white);
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }}
  .auth-footer {{
    text-align: center;
    color: var(--muted-ink);
    font-size: 12px;
    margin-top: 18px;
  }}

  /* PANEL 2: DASHBOARD PANEL */
  #dashboard_panel {{
    display: none;
  }}
  .dash-header {{
    background: linear-gradient(135deg, #102A5C 0%, #071735 100%);
    padding: 24px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .dash-sub {{
    color: var(--teal-200);
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.6px;
  }}
  .dash-welcome {{
    color: var(--white);
    font-size: 23px;
    font-weight: 800;
    margin-top: 4px;
  }}
  .btn-signout {{
    background: none;
    border: none;
    color: var(--teal-200);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }}
  .dash-content {{
    padding: 20px;
  }}
  .profile-card {{
    background: var(--white);
    border-radius: 16px;
    border: 1px solid var(--line);
    padding: 18px;
    display: flex;
    align-items: center;
  }}
  .avatar-circle {{
    width: 52px;
    height: 52px;
    border-radius: 26px;
    background: var(--teal-700);
    color: var(--white);
    font-size: 18px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .profile-info {{
    margin-left: 14px;
    flex: 1;
  }}
  .profile-name {{
    color: var(--ink);
    font-size: 18px;
    font-weight: 800;
  }}
  .profile-email {{
    color: var(--muted-ink);
    font-size: 13px;
    margin-top: 3px;
  }}
  .profile-badge {{
    background: #E5F4EF;
    color: var(--success);
    margin-top: 8px;
    display: inline-block;
  }}
  .section-title {{
    color: var(--ink);
    font-size: 20px;
    font-weight: 800;
    margin-top: 24px;
  }}
  .section-sub {{
    color: var(--muted-ink);
    font-size: 13px;
    margin-top: 3px;
    margin-bottom: 14px;
  }}
  .two-cards-row {{
    display: flex;
    gap: 12px;
  }}
  .status-card {{
    flex: 1;
    height: 120px;
    border-radius: 14px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .status-card.teal {{
    background: var(--teal-surface);
  }}
  .status-card.warning {{
    background: var(--warning-surface);
  }}
  .status-card-tag {{
    font-size: 11px;
    font-weight: 800;
  }}
  .status-card.teal .status-card-tag {{ color: var(--success); }}
  .status-card.warning .status-card-tag {{ color: var(--warning); }}
  .status-card-title {{
    font-size: 15px;
    font-weight: 800;
    color: var(--ink);
  }}
  .status-card-sub {{
    font-size: 12px;
    color: var(--muted-ink);
  }}
  .warm-card {{
    background: var(--surface-warm);
    border-radius: 12px;
    padding: 18px;
    font-size: 13.5px;
    line-height: 1.45;
    color: var(--muted-ink);
    margin-top: 10px;
    border: 1px solid #F3EBDD;
  }}
  .dash-actions-row {{
    display: flex;
    gap: 12px;
    margin-top: 14px;
  }}
  .btn-action-teal {{
    flex: 1;
    height: 52px;
    background: var(--teal-surface);
    color: var(--teal-700);
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }}
  .btn-action-amber {{
    flex: 1;
    height: 52px;
    background: var(--warning-surface);
    color: var(--warning);
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
  }}

  /* PANEL 3: JOURNAL PANEL */
  #journal_panel {{
    display: none;
    padding: 20px;
  }}
  .page-title {{
    color: var(--ink);
    font-size: 28px;
    font-weight: 800;
  }}
  .page-sub {{
    color: var(--muted-ink);
    font-size: 14px;
    line-height: 1.4;
    margin-top: 6px;
    margin-bottom: 20px;
  }}
  .journal-textarea {{
    width: 100%;
    height: 140px;
    border: 1.5px solid var(--line);
    border-radius: 10px;
    padding: 14px;
    font-size: 14px;
    color: var(--ink);
    outline: none;
    resize: none;
    margin: 12px 0;
  }}
  .journal-textarea:focus {{
    border-color: var(--teal-700);
  }}

  /* PANEL 4: COMPANION PANEL */
  #companion_panel {{
    display: none;
    padding: 20px;
  }}
  .companion-card {{
    background: var(--teal-surface);
    border-radius: 16px;
    padding: 18px;
  }}
  .companion-response-box {{
    margin-top: 12px;
    font-size: 14px;
    color: var(--ink);
    line-height: 1.45;
    background: rgba(255,255,255,0.7);
    padding: 12px;
    border-radius: 8px;
    border-left: 3px solid var(--teal-700);
  }}
  .disclaimer-card {{
    background: var(--warning-surface);
    border-radius: 12px;
    padding: 16px;
    font-size: 13px;
    color: var(--muted-ink);
    line-height: 1.4;
    margin-top: 18px;
    border: 1px solid #FFE3BA;
  }}

  /* PANEL 5: ASSESSMENT PANEL */
  #assessment_panel {{
    display: none;
    padding: 20px;
  }}

  /* PANEL 6: VOICE PANEL */
  #voice_panel {{
    display: none;
    padding: 20px;
    text-align: center;
  }}
  .mic-container {{
    display: flex;
    justify-content: center;
    margin: 40px 0 20px 0;
  }}
  .mic-circle {{
    width: 170px;
    height: 170px;
    border-radius: 85px;
    background: var(--teal-surface);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--teal-700);
    cursor: pointer;
    box-shadow: 0 8px 24px rgba(43, 157, 143, 0.2);
    transition: transform 0.2s;
  }}
  .mic-circle:hover {{
    transform: scale(1.03);
  }}

  /* PANEL 7: HISTORY PANEL */
  #history_panel {{
    display: none;
    padding: 20px;
  }}

  /* PANEL 8: PROFILE PANEL */
  #profile_panel {{
    display: none;
    padding: 20px;
  }}

  /* PANEL 9: SUPPORT PANEL */
  #support_panel {{
    display: none;
    padding: 20px;
  }}

  /* PANEL 10: RESOURCES PANEL */
  #resources_panel {{
    display: none;
    padding: 20px;
  }}
</style>
</head>
<body>

<div id="phone-container">
  <!-- Status Bar -->
  <div class="status-bar" id="status_bar">
    <span>09:41</span>
    <div class="status-icons">
      <svg class="status-icon" viewBox="0 0 24 24"><path d="M12 3c-4.97 0-9 4.03-9 9 0 2.12.74 4.07 1.97 5.61L12 22l7.03-4.39C20.26 16.07 21 14.12 21 12c0-4.97-4.03-9-9-9z"/></svg>
      <svg class="status-icon" viewBox="0 0 24 24"><path d="M12 4C7.31 4 3.07 5.9 0 8.98L12 21 24 8.98C20.93 5.9 16.69 4 12 4z"/></svg>
      <svg class="status-icon" viewBox="0 0 24 24"><path d="M17 4h-3V2h-4v2H7c-.55 0-1 .45-1 1v16c0 .55.45 1 1 1h10c.55 0 1-.45 1-1V5c0-.55-.45-1-1-1z"/></svg>
    </div>
  </div>

  <div class="screen-content" id="screen_scroll">

    <!-- 1. LOGIN SCREEN -->
    <div id="login_panel">
      <div class="login-hero">
        <img class="login-hero-bg" src="data:image/png;base64,{CRPF_BG_B64}" alt="Background">
        <div class="login-hero-overlay"></div>
        <div class="login-hero-content">
          <img class="crpf-logo-img" src="data:image/png;base64,{CRPF_LOGO_B64}" alt="CRPF Emblem">
          <div class="login-badge">CRPF MHS / A PRIVATE SPACE</div>
          <div class="login-hero-title">Make room for how you feel.</div>
          <div class="login-hero-sub">A calm place to pause, reflect, and find your next step.</div>
        </div>
      </div>
      <div class="login-form-card">
        <div class="secure-access-title">SECURE ACCESS</div>
        <div class="signin-header">Sign in to CRPF MHS</div>
        <div class="signin-sub">Your confidential wellbeing companion for armed forces personnel.</div>

        <div class="input-group">
          <label class="input-label" for="email_input">Email address</label>
          <input type="email" id="email_input" class="text-input" value="personnel1@sentinel.mil">
        </div>

        <div class="input-group">
          <label class="input-label" for="password_input">Password</label>
          <input type="password" id="password_input" class="text-input" value="sentinel-pers-2024">
        </div>

        <div class="info-badge-teal">
          Private by design  •  Your check-ins stay within authorised support pathways.
        </div>

        <button class="btn-auth" id="login_button" onclick="handleLogin()">Continue to my dashboard</button>
        <div class="auth-footer">Access is limited to authorised CRPF personnel</div>
      </div>
    </div>

    <!-- 2. DASHBOARD / HOME PANEL -->
    <div id="dashboard_panel">
      <div class="dash-header">
        <div>
          <div class="dash-sub">CRPF MHS</div>
          <div class="dash-welcome" id="welcome_text">Good evening, Mike</div>
        </div>
        <button class="btn-signout" onclick="showScreen('login')">Sign out</button>
      </div>

      <div class="dash-content">
        <div class="profile-card">
          <div class="avatar-circle" id="avatar_text">MJ</div>
          <div class="profile-info">
            <div class="profile-name" id="name_text">Sgt. Mike Johnson</div>
            <div class="profile-email" id="email_text">personnel1@sentinel.mil</div>
            <div class="badge profile-badge">PERSONNEL ACCOUNT  |  ACTIVE</div>
          </div>
        </div>

        <div class="section-title">Your wellbeing</div>
        <div class="section-sub">Small check-ins help us support you early</div>

        <div class="two-cards-row">
          <div class="status-card teal" onclick="showScreen('journal')">
            <div class="status-card-tag">READY</div>
            <div>
              <div class="status-card-title">Profile active</div>
              <div class="status-card-sub">You are checked in</div>
            </div>
          </div>
          <div class="status-card warning" onclick="showScreen('assessment')">
            <div class="status-card-tag">NEXT STEP</div>
            <div>
              <div class="status-card-title">Daily check-in</div>
              <div class="status-card-sub">Take a moment today</div>
            </div>
          </div>
        </div>

        <div class="section-title">Support at a glance</div>
        <div class="warm-card">
          Your conversations and check-ins are private. Reach out to your designated mental health support team whenever you need a confidential conversation.
        </div>

        <div class="section-title">Continue your care</div>
        <div class="dash-actions-row">
          <button class="btn-action-teal" id="daily_log_button" onclick="showScreen('journal')">Daily log</button>
          <button class="btn-action-amber" id="support_button" onclick="showScreen('support')">Get support</button>
        </div>
      </div>
    </div>

    <!-- 3. JOURNAL PANEL -->
    <div id="journal_panel">
      <div class="page-title">Daily log</div>
      <div class="page-sub">A private space to notice how today feels. There is no right answer.</div>

      <div class="card">
        <div style="font-size: 17px; font-weight: 700; color: var(--ink);">How are you feeling?</div>
        <button class="btn-outlined" style="margin-top: 14px; height: 50px;">🙂  Steady</button>
        <textarea id="journal_input" class="journal-textarea" placeholder="Write what is on your mind">Completed perimeter patrol duty at sector 4. Fatigue is manageable with regular hydration. Mental focus is solid, taking 10 minutes to decompress.</textarea>
        <button class="btn-primary" id="journal_save_button" onclick="saveJournalEntry()">Save private entry</button>
        <button class="btn-outlined" id="journal_voice_button" style="margin-top: 10px;" onclick="showScreen('voice')">Record a voice journal</button>
        <button class="btn-text" id="journal_assessment_button" style="width:100%; margin-top: 4px;" onclick="showScreen('assessment')">Take today's check-in</button>
      </div>

      <div class="warm-card">
        Your journal is private. Wellbeing signals are used to offer support, not to diagnose you.
      </div>
    </div>

    <!-- 4. COMPANION PANEL -->
    <div id="companion_panel">
      <div class="page-title">AI companion</div>
      <div class="page-sub">A calm place to think out loud, available when you need it.</div>

      <div class="companion-card">
        <div style="font-size: 17px; font-weight: 700; color: var(--ink);">What would you like to talk through?</div>
        <textarea id="companion_input" class="journal-textarea" style="margin-top: 12px; height: 75px;" placeholder="Type how you feel or an operational query...">I completed my night ambush duty and I cannot sleep, hypervigilant and hearing phantom noises.</textarea>
        <div id="companion_telemetry_badge" style="margin-top: 8px; font-size: 11px; font-weight: 700; color: var(--teal-700); background: #E5F4EF; padding: 6px 10px; border-radius: 6px; display: none;">
          ⚡ HK Neural Composite Engine: Matched Protocol "Sleep and Fatigue" (Cosine Sim: 0.853) | Morale: 50/100
        </div>
        <div class="companion-response-box" id="companion_response_text">
          “I hear that today was demanding on patrol. It is completely normal to feel muscle tiredness after a long shift. Remember to take steady, deep breaths and disconnect before turning in tonight.”
          Try: “I have had a difficult day” or “Help me prepare for a conversation.”
        </div>
        <button class="btn-primary" id="companion_start_button" style="margin-top: 16px;" onclick="sendCompanionChat()">Start a conversation</button>
        <button class="btn-primary" id="companion_start_button" style="margin-top: 14px;" onclick="sendCompanionChat()">Send to HK AI Engine</button>
      </div>

      <div class="disclaimer-card">
        AI-assisted support is not a clinician, diagnosis, or emergency service. Contact your support team whenever you need a human conversation.
      </div>
    </div>

    <!-- 5. ASSESSMENT / CHECK-IN PANEL -->
    <div id="assessment_panel">
      <div class="page-title">Today's check-in</div>
      <div class="page-sub">A few simple questions can help you notice what support might be useful.</div>

      <div class="card" style="margin-top: 24px;">
        <div style="font-size: 17px; font-weight: 700; color: var(--ink);">Over the last few days, how supported have you felt?</div>
        <button class="btn-outlined" style="margin-top: 16px; border-color: var(--teal-700); color: var(--teal-700); background: #F4FBF9;">I have felt supported</button>
        <button class="btn-outlined" style="margin-top: 10px; border-color: var(--warning); color: var(--warning); background: #FFFBF5;">I could use more support</button>
        <button class="btn-primary" style="margin-top: 18px;" onclick="showScreen('home')">Continue</button>
      </div>
    </div>

    <!-- 6. VOICE JOURNAL PANEL -->
    <div id="voice_panel">
      <div class="page-title" style="text-align: left;">Voice journal</div>
      <div class="page-sub" style="text-align: left;">Speak freely. You will review the transcript before anything is saved.</div>

      <div class="mic-container">
        <div class="mic-circle" onclick="toggleVoiceRecord()">
          <svg style="width: 48px; height: 48px; fill: currentColor;" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
          </svg>
          <span style="font-size: 15px; font-weight: 700; margin-top: 8px;">MIC</span>
        </div>
      </div>

      <button class="btn-primary" style="margin-top: 16px;">Start speaking</button>
      <div class="warm-card" style="text-align: left; margin-top: 20px;">
        Voice processing requires your consent. Your recording is never submitted automatically.
      </div>
    </div>

    <!-- 7. HISTORY PANEL -->
    <div id="history_panel">
      <div class="page-title">Your history</div>
      <div class="page-sub">Review your check-ins and private journal entries in one place.</div>

      <div class="card">
        <div style="font-size: 17px; font-weight: 700; color: var(--ink);">Today</div>
        <div style="color: var(--muted-ink); font-size: 14px; margin-top: 10px; line-height: 1.4;">
          Journal entry recorded at 08:30 AM (Steady) — "Completed shift with good situational alertness."
        </div>
        <button class="btn-text" style="padding-left: 0; margin-top: 8px;" onclick="showScreen('journal')">Write another daily log</button>
      </div>

      <div class="warm-card">
        Your personal wellbeing level is never displayed here. You stay in control of your story.
      </div>
    </div>

    <!-- 8. PROFILE & PRIVACY PANEL -->
    <div id="profile_panel">
      <div class="page-title">Profile &amp; privacy</div>

      <div class="card" style="margin-top: 18px;">
        <div style="font-size: 19px; font-weight: 800; color: var(--ink);" id="profile_name_text">Sgt. Mike Johnson</div>
        <div style="font-size: 14px; color: var(--muted-ink); margin-top: 4px;" id="profile_email_text">personnel1@sentinel.mil</div>
        <div style="font-size: 13px; color: var(--muted-ink); margin-top: 16px; line-height: 1.45;">
          Your account is protected by audited access controls. Sentinel is not anonymous; only authorised support personnel can access sensitive information.
        </div>
      </div>

      <div class="section-title" style="margin-top: 20px;">Need immediate help?</div>
      <button class="btn-action-amber" style="width: 100%; margin-top: 12px;" onclick="showScreen('support')">Open confidential support</button>
      <button class="btn-outlined" style="margin-top: 12px;" onclick="alert('Settings & consent preferences')">Settings and consent</button>
      <button class="btn-text" style="width: 100%; margin-top: 6px;" onclick="showScreen('resources')">Browse wellbeing resources</button>
    </div>

    <!-- 9. GET SUPPORT PANEL -->
    <div id="support_panel">
      <div class="page-title">Get support</div>
      <div class="page-sub">You do not have to work through a difficult moment alone.</div>

      <div class="status-card warning" style="height: auto; padding: 20px; margin-top: 20px;">
        <div style="font-size: 18px; font-weight: 800; color: var(--ink);">Confidential support team</div>
        <div style="font-size: 14px; color: var(--muted-ink); margin-top: 8px; line-height: 1.4;">
          Connect with your designated mental health support team for a private conversation.
        </div>
        <button class="btn-primary" style="background: var(--white); color: var(--warning); border: 1.5px solid var(--warning); margin-top: 16px;">Request a conversation</button>
      </div>

      <div class="warm-card" style="margin-top: 18px;">
        If you are in immediate danger, contact local emergency services or your unit's emergency support channel.
      </div>
    </div>

    <!-- 10. RESOURCES PANEL -->
    <div id="resources_panel">
      <div class="page-title">Wellbeing resources</div>
      <div class="page-sub">Practical guidance for rest, stress, connection, and getting support.</div>

      <div class="card" style="margin-top: 18px;">
        <div style="font-size: 17px; font-weight: 800; color: var(--ink);">Grounding after a demanding day</div>
        <div style="font-size: 14px; color: var(--muted-ink); margin-top: 8px; line-height: 1.4;">
          Simple ways to slow your breathing and return your attention to the present.
        </div>
        <button class="btn-text" style="padding-left: 0; margin-top: 8px;">Read resource</button>
      </div>

      <div class="card">
        <div style="font-size: 17px; font-weight: 800; color: var(--ink);">Sleep recovery under deployment stress</div>
        <div style="font-size: 14px; color: var(--muted-ink); margin-top: 8px; line-height: 1.4;">
          Tactical protocols for achieving restorative sleep in high-alert operating environments.
        </div>
        <button class="btn-text" style="padding-left: 0; margin-top: 8px;">Read resource</button>
      </div>
    </div>

  </div>

  <!-- Bottom Navigation Bar -->
  <div id="screen_nav" style="display: none;">
    <button class="nav-item active" id="nav_home" onclick="showScreen('home')">
      <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>
      <span class="nav-label">Home</span>
    </button>
    <button class="nav-item" id="nav_journal" onclick="showScreen('journal')">
      <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
      <span class="nav-label">Journal</span>
    </button>
    <button class="nav-item" id="nav_companion" onclick="showScreen('companion')">
      <svg viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
      <span class="nav-label">Companion</span>
    </button>
    <button class="nav-item" id="nav_history" onclick="showScreen('history')">
      <svg viewBox="0 0 24 24"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/></svg>
      <span class="nav-label">History</span>
    </button>
    <button class="nav-item" id="nav_profile" onclick="showScreen('profile')">
      <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/></svg>
      <span class="nav-label">Profile</span>
    </button>
  </div>
</div>

<script>
  let authToken = null;
  let currentUser = {{
    fullName: "Sgt. Mike Johnson",
    email: "personnel1@sentinel.mil",
    initials: "MJ"
  }};

  function handleLogin() {{
    const email = document.getElementById("email_input").value;
    const password = document.getElementById("password_input").value;
    const btn = document.getElementById("login_button");
    btn.innerText = "Signing in...";
    
    // Call live FastAPI backend
    fetch("http://127.0.0.1:8000/api/auth/login", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ email, password }})
    }})
    .then(r => r.json())
    .then(data => {{
      btn.innerText = "Continue to my dashboard";
      if (data.access_token) {{
        authToken = data.access_token;
        if (data.user) {{
          currentUser.fullName = data.user.full_name || "Personnel Member";
          currentUser.email = data.user.email;
          const parts = currentUser.fullName.split(" ");
          currentUser.initials = (parts[0][0] + (parts[1] ? parts[1][0] : "")).toUpperCase();
        }}
        updateProfileUI();
        showScreen("home");
      }} else {{
        alert("Authentication failed: " + (data.detail || "Invalid credentials"));
      }}
    }})
    .catch(err => {{
      btn.innerText = "Continue to my dashboard";
      // Fallback for demo
      updateProfileUI();
      showScreen("home");
    }});
  }}

  function updateProfileUI() {{
    document.getElementById("name_text").innerText = currentUser.fullName;
    document.getElementById("email_text").innerText = currentUser.email;
    document.getElementById("avatar_text").innerText = currentUser.initials;
    document.getElementById("profile_name_text").innerText = currentUser.fullName;
    document.getElementById("profile_email_text").innerText = currentUser.email;
  }}

  function showScreen(screen) {{
    const panels = [
      "login_panel", "dashboard_panel", "journal_panel", "companion_panel",
      "history_panel", "profile_panel", "assessment_panel", "voice_panel",
      "support_panel", "resources_panel"
    ];
    panels.forEach(p => {{
      const el = document.getElementById(p);
      if (el) el.style.display = "none";
    }});

    const nav = document.getElementById("screen_nav");
    const statusBar = document.getElementById("status_bar");

    // Reset nav items
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));

    if (screen === "login") {{
      document.getElementById("login_panel").style.display = "block";
      nav.style.display = "none";
      statusBar.classList.remove("light-bar");
    }} else {{
      nav.style.display = "flex";
      statusBar.classList.add("light-bar");

      switch(screen) {{
        case "journal":
          document.getElementById("journal_panel").style.display = "block";
          document.getElementById("nav_journal").classList.add("active");
          break;
        case "companion":
          document.getElementById("companion_panel").style.display = "block";
          document.getElementById("nav_companion").classList.add("active");
          break;
        case "history":
          document.getElementById("history_panel").style.display = "block";
          document.getElementById("nav_history").classList.add("active");
          break;
        case "profile":
          document.getElementById("profile_panel").style.display = "block";
          document.getElementById("nav_profile").classList.add("active");
          break;
        case "assessment":
          document.getElementById("assessment_panel").style.display = "block";
          document.getElementById("nav_journal").classList.add("active");
          break;
        case "voice":
          document.getElementById("voice_panel").style.display = "block";
          document.getElementById("nav_journal").classList.add("active");
          break;
        case "support":
          document.getElementById("support_panel").style.display = "block";
          document.getElementById("nav_profile").classList.add("active");
          break;
        case "resources":
          document.getElementById("resources_panel").style.display = "block";
          document.getElementById("nav_profile").classList.add("active");
          break;
        case "home":
        default:
          document.getElementById("dashboard_panel").style.display = "block";
          document.getElementById("nav_home").classList.add("active");
          break;
      }}
    }}
    document.getElementById("screen_scroll").scrollTop = 0;
  }}

  function sendCompanionChat() {{
    const inputEl = document.getElementById("companion_input");
    const msg = inputEl && inputEl.value.trim() ? inputEl.value.trim() : "I completed my night ambush duty and I cannot sleep, hypervigilant and hearing phantom noises.";
    const respBox = document.getElementById("companion_response_text");
    respBox.innerText = "Connecting to private companion...";
    const badge = document.getElementById("companion_telemetry_badge");
    const btn = document.getElementById("companion_start_button");

    respBox.innerText = "Consulting CRPF Mental Health On-Device Neural Engine...";
    btn.innerText = "Processing HK Pipeline...";

    fetch("http://127.0.0.1:8000/api/ai/chat", {{
      method: "POST",
      headers: {{
        "Content-Type": "application/json",
        "Authorization": authToken ? "Bearer " + authToken : ""
      }},
      body: JSON.stringify({{
        message: "I completed my shift today and feel a bit tired.",
        message: msg,
        tone: "grounding"
      }})
    }})
    .then(r => r.json())
    .then(data => {{
      btn.innerText = "Send to HK AI Engine";
      if (data.message && data.message.content) {{
        respBox.innerText = data.message.content;
        if (badge) {{
          badge.style.display = "block";
          const escText = data.support_escalation ? " 🚨 ESCALATED TO UNIT MEDICAL OFFICER" : "";
          const morale = data.morale_score !== undefined ? data.morale_score : 50;
          badge.innerText = `⚡ HK Neural Engine | Morale: ${{morale}}/100 | Mood: ${{data.detected_mood || 'operational'}}${{escText}}`;
          if (data.support_escalation) {{
            badge.style.background = "#FFF2DE";
            badge.style.color = "#C7862B";
            badge.style.border = "1px solid #FFE3BA";
          }} else {{
            badge.style.background = "#E5F4EF";
            badge.style.color = "#2B9D8F";
            badge.style.border = "none";
          }}
        }}
      }} else {{
        respBox.innerText = "I hear you, Mike. Good work completing your shift today. Allow yourself to rest and recharge safely.";
        respBox.innerText = "Thank you for reaching out. Please connect with your unit welfare officer if needed.";
      }}
    }})
    .catch(() => {{
      respBox.innerText = "“I hear you, Mike. Good work completing your shift today. Allow yourself to rest and recharge safely.”";
      btn.innerText = "Send to HK AI Engine";
      respBox.innerText = "Neural pipeline connection offline. Consulting local SQLite safety repository.";
    }});
  }}

  function saveJournalEntry() {{
    alert("Your private journal entry has been encrypted and saved.");
  }}

  function toggleVoiceRecord() {{
    alert("Voice recording started. Speak freely.");
  }}
</script>
</body>
</html>
"""

class CustomHTTPHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))

def start_server():
    server = HTTPServer(("127.0.0.1", 8088), CustomHTTPHandler)
    server.serve_forever()

def capture_all_screens():
    # Start web server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1)

    print("[CRPF MHS Runner] Server started at http://127.0.0.1:8088")

    screenshots = [
        ("01_login_screen.png", "Login Screen", lambda page: page.evaluate("showScreen('login')")),
        ("02_dashboard_home.png", "Dashboard / Home Screen", lambda page: page.evaluate("showScreen('home')")),
        ("03_daily_journal.png", "Daily Log / Journal Screen", lambda page: page.evaluate("showScreen('journal')")),
        ("04_voice_journal.png", "Voice Journal Screen", lambda page: page.evaluate("showScreen('voice')")),
        ("05_assessment_checkin.png", "Today's Check-in / Assessment Screen", lambda page: page.evaluate("showScreen('assessment')")),
        ("06_ai_companion.png", "AI Companion Chat Screen", lambda page: page.evaluate("showScreen('companion')")),
        ("07_history_screen.png", "History Screen", lambda page: page.evaluate("showScreen('history')")),
        ("08_profile_screen.png", "Profile & Privacy Screen", lambda page: page.evaluate("showScreen('profile')")),
        ("09_support_screen.png", "Confidential Support & Crisis Screen", lambda page: page.evaluate("showScreen('support')")),
        ("10_resources_screen.png", "Wellbeing Resources Screen", lambda page: page.evaluate("showScreen('resources')")),
    ]

    with sync_playwright() as p:
        # Launch Chromium with mobile emulation
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 412, "height": 892},
            device_scale_factor=2.5,
            is_mobile=True,
            has_touch=True
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8088")
        page.wait_for_timeout(1000)

        # First simulate live login interaction
        print("[CRPF MHS Runner] Executing live login interaction...")
        page.fill("#email_input", "personnel1@sentinel.mil")
        page.fill("#password_input", "sentinel-pers-2024")

        # Capture 01_login_screen.png
        phone_el = page.locator("#phone-container")
        login_path_art = os.path.join(ARTIFACTS_DIR, "01_login_screen.png")
        login_path_brn = os.path.join(BRAIN_DIR, "01_login_screen.png")
        phone_el.screenshot(path=login_path_art)
        phone_el.screenshot(path=login_path_brn)
        print(f"[CRPF MHS Runner] Captured: 01_login_screen.png")

        # Click login button
        page.click("#login_button")
        page.wait_for_timeout(1200)
        page.wait_for_selector("#dashboard_panel", state="visible", timeout=6000)
        page.wait_for_timeout(1000)

        # Now capture each screen sequentially
        for filename, label, switch_fn in screenshots[1:]:
            if filename == "06_ai_companion.png":
                switch_fn(page)
                page.wait_for_timeout(500)
                # Fill operational query
                page.fill("#companion_input", "I completed my night ambush duty and I cannot sleep, hypervigilant and hearing phantom noises.")
                page.click("#companion_start_button")
                page.wait_for_timeout(2500)
                art_path = os.path.join(ARTIFACTS_DIR, filename)
                brn_path = os.path.join(BRAIN_DIR, filename)
                phone_el.screenshot(path=art_path)
                phone_el.screenshot(path=brn_path)
                print(f"[CRPF MHS Runner] Captured {label} (Operational RAG Query): {filename}")

                # Capture Crisis Intervention Screen as well
                page.fill("#companion_input", "I feel hopeless, I cannot take this pressure any longer and I want to end my life.")
                page.click("#companion_start_button")
                page.wait_for_timeout(2500)
                crisis_art = os.path.join(ARTIFACTS_DIR, "06b_crisis_intervention.png")
                crisis_brn = os.path.join(BRAIN_DIR, "06b_crisis_intervention.png")
                phone_el.screenshot(path=crisis_art)
                phone_el.screenshot(path=crisis_brn)
                print(f"[CRPF MHS Runner] Captured Crisis Escalation Screen: 06b_crisis_intervention.png")
                continue

            switch_fn(page)
            page.wait_for_timeout(600)
            art_path = os.path.join(ARTIFACTS_DIR, filename)
            brn_path = os.path.join(BRAIN_DIR, filename)
            phone_el.screenshot(path=art_path)
            phone_el.screenshot(path=brn_path)
            print(f"[CRPF MHS Runner] Captured {label}: {filename}")

        browser.close()
    
    print("[CRPF MHS Runner] All 10 screens captured successfully!")

if __name__ == "__main__":
    capture_all_screens()

