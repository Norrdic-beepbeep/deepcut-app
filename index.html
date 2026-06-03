<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>DeepCut // Video Compliance</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect"shref="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --c-bg: 234 227 210;
            --c-text: 45 40 36;
            --c-card: 253 251 247;
            --c-acc1: 210 145 30;
            --c-acc2: 64 99 90;
            --c-acc3: 180 80 68;
            --c-success: 75 115 80;
            --c-muted: 105 95 85;
            --c-subtext: 80 72 64;
        }

        [data-theme="fox"] {
            --c-bg: 227 211 181;
            --c-text: 62 39 35;
            --c-card: 245 239 230;
            --c-acc1: 195 115 35;
            --c-acc2: 110 80 70;
            --c-acc3: 165 55 45;
            --c-success: 85 115 85;
            --c-muted: 115 95 85;
            --c-subtext: 93 64 55;
        }

        [data-theme="silver"] {
            --c-bg: 20 20 22;
            --c-text: 235 235 240;
            --c-card: 38 38 40;
            --c-acc1: 160 160 165;
            --c-acc2: 90 90 95;
            --c-acc3: 220 220 225;
            --c-success: 242 242 247;
            --c-muted: 175 175 180;
            --c-subtext: 210 210 215;
        }

        body { font-family: 'Jost', sans-serif; transition: background-color 0.4s ease, color 0.4s ease; }
        .font-typewriter { font-family: 'Courier Prime', monospace; }
        .progress-transition { transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
        .shadow-hard { box-shadow: 4px 4px 0px rgb(var(--c-text)); }
        @media (min-width: 640px) { .shadow-hard { box-shadow: 8px 8px 0px rgb(var(--c-text)); } }
        .shadow-hard-sm { box-shadow: 3px 3px 0px rgb(var(--c-text)); }
        .shadow-hard-hover:hover:not(:disabled) { box-shadow: 6px 6px 0px rgb(var(--c-text)); transform: translate(-2px, -2px); }
        .shadow-hard-active:active:not(:disabled) { box-shadow: 2px 2px 0px rgb(var(--c-text)); transform: translate(2px, 2px); }
        .req-met { color: rgb(var(--c-success)); text-decoration: line-through; text-decoration-thickness: 2px; }
        .req-unmet { color: rgb(var(--c-muted)); }
        .fade-hidden { opacity: 0; pointer-events: none; position: absolute; transform: translateY(-10px); }
        .fluid-title { font-size: clamp(2.5rem, 6vw, 4rem); line-height: 1.1; }
        .fluid-subtitle { font-size: clamp(1rem, 2vw, 1.125rem); }

        @media (max-width: 768px) {
            .adaptive-table, .adaptive-table tbody, .adaptive-table tr, .adaptive-table td { display: block; width: 100%; }
            .adaptive-table thead { display: none; }
            .adaptive-table tr { margin-bottom: 1.5rem; border: 3px solid rgb(var(--c-text)); background: rgb(var(--c-card)); }
            .adaptive-table td { position: relative; padding: 1.25rem !important; border: none !important; border-bottom: 2px dashed rgb(var(--c-bg)) !important; }
            .adaptive-table td:last-child { border-bottom: none !important; }
            .adaptive-table td::before { content: attr(data-label); display: block; font-family: 'Courier Prime', monospace; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: rgb(var(--c-muted)); margin-bottom: 0.5rem; }
        }
        button:focus-visible, input:focus-visible, a:focus-visible { outline: 3px solid rgb(var(--c-acc1)) !important; outline-offset: 2px !important; }
    </style>
    <script>
        tailwind.config = { theme: { extend: { colors: { cBg: 'rgb(var(--c-bg) / <alpha-value>)', cText: 'rgb(var(--c-text) / <alpha-value>)', cCard: 'rgb(var(--c-card) / <alpha-value>)', cAcc1: 'rgb(var(--c-acc1) / <alpha-value>)', cAcc2: 'rgb(var(--c-acc2) / <alpha-value>)', cAcc3: 'rgb(var(--c-acc3) / <alpha-value>)', cSuccess: 'rgb(var(--c-success) / <alpha-value>)', cMuted: 'rgb(var(--c-muted) / <alpha-value>)', cSubtext: 'rgb(var(--c-subtext) / <alpha-value>)' } } } }
    </script>
</head>
<body class="bg-cBg text-cText min-h-screen flex flex-col items-center justify-start p-4 sm:p-6 relative overflow-x-hidden selection:bg-cAcc1 selection:text-cText transition-colors duration-300">

    <a href="#mainContent" class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-cCard focus:text-cText focus:border-4 focus:border-cText focus:shadow-hard font-bold uppercase tracking-wider text-sm">Skip to main content</a>

    <div id="vaultDrawer" class="fixed inset-y-0 left-0 w-[290px] sm:w-[350px] bg-cCard border-r-[4px] border-cText z-50 transform -translate-x-full transition-transform duration-300 ease-in-out flex flex-col shadow-hard" role="dialog" aria-modal="true" aria-label="Vault Archive">
        <div class="p-6 border-b-[3px] border-cText flex justify-between items-center bg-cBg/30">
            <h3 class="text-lg font-bold tracking-widest uppercase font-typewriter">📁 Vault Archive</h3>
            <button id="closeVaultBtn" class="text-2xl font-bold text-cText hover:text-cAcc3 focus:outline-none p-2" aria-label="Close Vault Archive">&times;</button>
        </div>
        
        <div class="p-3 px-4 border-b-[3px] border-cText bg-cBg/50 flex justify-between items-center">
            <label for="vaultSort" class="text-[10px] sm:text-xs font-bold tracking-widest uppercase text-cText">Sort By:</label>
            <select id="vaultSort" class="bg-cCard border-[2px] border-cText text-[10px] sm:text-xs font-bold font-typewriter p-1.5 focus:outline-none focus:ring-2 focus:ring-cAcc1 cursor-pointer">
                <option value="date-desc">Newest First</option>
                <option value="date-asc">Oldest First</option>
                <option value="name-asc">File Name (A-Z)</option>
                <option value="errors-desc">Most Errors</option>
            </select>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-4" id="vaultList">
            <p class="text-center text-cMuted text-xs font-typewriter uppercase mt-10">No compliance logs stored</p>
        </div>
    </div>
    <div id="vaultOverlay" class="fixed inset-0 bg-cText/60 z-40 hidden transition-opacity duration-300 opacity-0" aria-hidden="true"></div>

    <div id="authContainer" class="w-full max-w-lg mx-auto mt-8 sm:mt-16 z-20 transition-all duration-500 relative px-2 sm:px-0">
        <div id="loginScreen" class="bg-cCard border-[3px] sm:border-[4px] border-cText p-8 sm:p-10 shadow-hard relative overflow-hidden transition-all duration-500 w-full mb-4 mr-2 sm:mr-3">
            <div class="text-center mb-8 border-b-[3px] border-cText pb-6">
                <span class="text-4xl mb-3 block" aria-hidden="true">🔐</span>
                <h1 class="text-3xl sm:text-4xl font-bold tracking-tight uppercase" style="letter-spacing: -0.02em;">DeepCut Access</h1>
                <p class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 uppercase tracking-widest font-bold">Authorized Personnel Only</p>
            </div>
            <div class="space-y-6">
                <div>
                    <label for="loginUsername" class="block text-cText text-xs font-bold tracking-widest uppercase mb-2">Username or Email</label>
                    <input type="text" id="loginUsername" placeholder="Enter username or email" class="w-full bg-cBg/50 border-[3px] border-cText text-cText px-4 py-4 sm:px-5 focus:outline-none focus:bg-cBg transition-colors text-base font-typewriter placeholder:text-cMuted font-bold shadow-hard-sm">
                </div>
                <div>
                    <label for="loginPassword" class="block text-cText text-xs font-bold tracking-widest uppercase mb-2">Password</label>
                    <input type="password" id="loginPassword" placeholder="Enter password" class="w-full bg-cBg/50 border-[3px] border-cText text-cText px-4 py-4 sm:px-5 focus:outline-none focus:bg-cBg transition-colors text-base font-typewriter placeholder:text-cMuted font-bold shadow-hard-sm">
                </div>
                <button id="loginBtn" class="w-full bg-cAcc3 text-cCard font-bold px-6 py-4 uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all text-sm sm:text-base mt-4">Authorize</button>
                <div class="flex justify-between items-center mt-6 border-t-[2px] border-cText/20 pt-6">
                    <button id="showForgotBtn" class="text-xs sm:text-sm font-bold tracking-widest uppercase text-cAcc1 hover:text-cAcc3 transition-colors focus:outline-none p-1">Forgot Password?</button>
                    <button id="showRegisterBtn" class="text-xs sm:text-sm font-bold tracking-widest uppercase text-cAcc2 hover:text-cAcc3 transition-colors focus:outline-none p-1">Register &rarr;</button>
                </div>
            </div>
        </div>

        <div id="registerScreen" class="bg-cCard border-[3px] sm:border-[4px] border-cText p-8 sm:p-10 shadow-hard relative overflow-hidden fade-hidden transition-all duration-500 w-full mb-4 mr-2 sm:mr-3">
            <div class="text-center mb-6 border-b-[3px] border-cText pb-6">
                <span class="text-4xl mb-3 block" aria-hidden="true">🛡️</span>
                <h1 class="text-3xl font-bold tracking-tight uppercase" style="letter-spacing: -0.02em;">Engine Registration</h1>
                <p class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 uppercase tracking-widest font-bold">Create Credentials</p>
            </div>
            <div class="space-y-4">
                <div>
                    <label for="regName" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">Full Name</label>
                    <input type="text" id="regName" placeholder="e.g. John Doe" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <div>
                    <label for="regUsername" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">Username</label>
                    <input type="text" id="regUsername" placeholder="e.g. johndoe99" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <div>
                    <label for="regEmail" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">Email Address</label>
                    <input type="email" id="regEmail" placeholder="operator@company.com" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <div>
                    <label for="regPassword" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">Password</label>
                    <input type="password" id="regPassword" placeholder="Create a secure password" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <div class="bg-cBg/30 border-[2px] border-cText p-3 shadow-inner">
                    <ul class="space-y-2 text-xs font-typewriter font-bold" id="validationList">
                        <li id="reqLength" class="req-unmet transition-all duration-300 flex items-center gap-2"><span class="status-icon" aria-hidden="true">○</span> Min 12 characters</li>
                        <li id="reqUpper" class="req-unmet transition-all duration-300 flex items-center gap-2"><span class="status-icon" aria-hidden="true">○</span> One uppercase letter</li>
                        <li id="reqSpecial" class="req-unmet transition-all duration-300 flex items-center gap-2"><span class="status-icon" aria-hidden="true">○</span> One special character</li>
                    </ul>
                </div>
                <button id="registerBtn" disabled class="w-full bg-cAcc2 disabled:bg-cMuted disabled:cursor-not-allowed text-cBg font-bold px-6 py-4 uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all mt-4 text-sm sm:text-base">Create Operator</button>
                <div class="text-center mt-6 border-t-[2px] border-cText/20 pt-4">
                    <button id="showLoginBtn" class="text-xs sm:text-sm font-bold tracking-widest uppercase text-cAcc3 hover:text-cAcc2 transition-colors focus:outline-none p-1">&larr; Back to Login</button>
                </div>
            </div>
        </div>

        <div id="forgotPasswordScreen" class="bg-cCard border-[3px] sm:border-[4px] border-cText p-8 sm:p-10 shadow-hard relative overflow-hidden fade-hidden transition-all duration-500 w-full mb-4 mr-2 sm:mr-3">
            <div class="text-center mb-6 border-b-[3px] border-cText pb-6">
                <span class="text-4xl mb-3 block" aria-hidden="true">🔑</span>
                <h1 class="text-3xl font-bold tracking-tight uppercase" style="letter-spacing: -0.02em;">System Recovery</h1>
                <p class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 uppercase tracking-widest font-bold">Request Access Reset</p>
            </div>
            <div class="space-y-6">
                <p class="text-sm font-medium text-cText leading-relaxed">Enter your registered email address below. If an account matches, a secure link to reset your password will be dispatched.</p>
                <div>
                    <label for="resetEmail" class="block text-cText text-xs font-bold tracking-widest uppercase mb-2">Email Address</label>
                    <input type="email" id="resetEmail" placeholder="operator@company.com" class="w-full bg-cBg/50 border-[3px] border-cText text-cText px-4 py-4 sm:px-5 focus:outline-none focus:bg-cBg transition-colors text-base font-typewriter placeholder:text-cMuted font-bold shadow-hard-sm">
                </div>
                <button id="sendResetBtn" class="w-full bg-cAcc1 text-cCard font-bold px-6 py-4 uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all mt-4 text-sm sm:text-base">Send Reset Link</button>
                <div class="text-center mt-6 border-t-[2px] border-cText/20 pt-4">
                    <button id="backToLoginFromForgotBtn" class="text-xs sm:text-sm font-bold tracking-widest uppercase text-cAcc3 hover:text-cAcc2 transition-colors focus:outline-none p-1">&larr; Back to Login</button>
                </div>
            </div>
        </div>
    </div>

    <div id="appScreen" class="w-full max-w-5xl mx-auto space-y-8 sm:space-y-12 mt-6 sm:mt-10 relative z-10 hidden opacity-0 transition-opacity duration-700 px-0 sm:px-4">
        
        <header class="w-full flex flex-col border-b-[3px] sm:border-b-4 border-cText pb-6 sm:pb-8 relative">
            <div class="text-center w-full">
                <div class="inline-flex items-center justify-center space-x-2 bg-cCard border-[2px] sm:border-[3px] border-cText px-4 py-1.5 shadow-hard-sm mb-6">
                    <span class="w-2.5 h-2.5 rounded-full bg-cSuccess animate-pulse border border-cText" aria-hidden="true"></span>
                    <span class="text-xs font-bold uppercase tracking-[0.2em] text-cText">System Operational</span>
                </div>
                <h1 class="fluid-title font-bold tracking-tight uppercase" style="letter-spacing: -0.02em;">DeepCut Engine</h1>
                <p class="text-cSubtext w-full max-w-2xl mx-auto fluid-subtitle font-medium tracking-wide mt-4 px-4">Automated cinematic auditing for continuity, copyright compliance, and visual consistency.</p>
            </div>
            <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center w-full pt-8 gap-4 px-2 sm:px-0">
                <div class="flex flex-row items-center gap-3">
                    <div class="h-12 flex-1 sm:flex-none flex items-center justify-center sm:justify-start bg-cSuccess text-cBg border-[2px] sm:border-[3px] border-cText px-4 shadow-hard-sm">
                        <span class="text-xs font-bold tracking-[0.2em] uppercase opacity-80 mr-2">Operator:</span>
                        <span id="displayUsername" class="font-typewriter text-xs sm:text-sm font-bold uppercase tracking-widest truncate max-w-[120px] sm:max-w-[200px]">UNKNOWN</span>
                    </div>
                    <button id="changePassBtn" class="h-12 flex items-center justify-center bg-cBg text-cText hover:bg-cAcc1 hover:text-cBg border-[2px] sm:border-[3px] border-cText px-4 text-xs font-bold tracking-[0.2em] uppercase shadow-hard-sm transition-colors" title="Change Access Code">Key 🔑</button>
                    <button id="logoutBtn" class="h-12 flex items-center justify-center bg-cBg text-cText hover:bg-cAcc3 hover:text-cBg border-[2px] sm:border-[3px] border-cText px-4 text-xs font-bold tracking-[0.2em] uppercase shadow-hard-sm transition-colors">Log Out ⏏</button>
                </div>
                <div class="flex gap-3 w-full sm:w-auto">
                    <button id="vaultBtn" class="flex-1 sm:flex-none h-12 flex items-center justify-center bg-cCard text-cText hover:bg-cBg border-[2px] sm:border-[3px] border-cText px-4 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase shadow-hard-sm shadow-hard-hover transition-all">📁 Vault</button>
                    <button id="themeToggleBtn" class="flex-1 sm:flex-none h-12 flex items-center justify-center bg-cCard text-cText hover:bg-cBg border-[2px] sm:border-[3px] border-cText px-4 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase shadow-hard-sm shadow-hard-hover transition-all">🎨 Standard</button>
                    <button id="guideBtn" class="flex-1 sm:flex-none h-12 flex items-center justify-center bg-cCard text-cText hover:bg-cBg border-[2px] sm:border-[3px] border-cText px-4 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase shadow-hard-sm shadow-hard-hover transition-all">Guide 📖</button>
                </div>
            </div>
        </header>

        <main id="mainContent" class="bg-cCard border-[3px] sm:border-[4px] border-cText p-6 sm:p-12 shadow-hard relative overflow-hidden mb-4 mr-2 sm:mr-3">
            <div id="inputWorkspace" class="space-y-6 sm:space-y-10 transition-opacity duration-300">
                <label for="fileInput" id="uploadZone" class="group w-full block border-[3px] border-dashed border-cText bg-cBg/50 hover:bg-cAcc1/20 p-8 sm:p-12 text-center cursor-pointer transition-colors duration-300">
                    <input type="file" id="fileInput" class="sr-only" accept=".xml,.fcpxml,.edl,.mp4" aria-describedby="fileFormatsHelp" />
                    <div class="space-y-4 pointer-events-none flex flex-col items-center">
                        <div class="text-5xl sm:text-6xl mb-2 transition-transform duration-300 group-hover:scale-110" aria-hidden="true">📂</div>
                        <div>
                            <div class="text-cText font-bold text-lg sm:text-xl uppercase tracking-wide">Select or drag timeline</div>
                            <div id="fileFormatsHelp" class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 font-bold">Supports XML, FCPXML, EDL, MP4</div>
                        </div>
                    </div>
                </label>
                <div class="flex items-center justify-center space-x-4">
                    <div class="h-[2px] sm:h-[3px] bg-cText w-full" aria-hidden="true"></div>
                    <span class="text-cText text-xs sm:text-sm font-bold tracking-[0.2em] uppercase px-4">OR</span>
                    <div class="h-[2px] sm:h-[3px] bg-cText w-full" aria-hidden="true"></div>
                </div>
                <div class="flex flex-col sm:flex-row gap-4 w-full relative">
                    <label for="urlInput" class="sr-only">Paste media link here</label>
                    <input type="url" id="urlInput" placeholder="Paste media link here..." class="w-full flex-1 bg-cCard border-[2px] sm:border-[3px] border-cText text-cText px-4 py-4 sm:px-5 focus:outline-none focus:bg-cBg transition-colors text-sm sm:text-base font-typewriter placeholder:text-cMuted font-bold shadow-hard-sm">
                    <button id="runUrlBtn" class="w-full sm:w-auto bg-cAcc2 text-cBg font-bold px-6 py-4 sm:px-8 text-sm sm:text-base uppercase tracking-widest border-[2px] sm:border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all whitespace-nowrap">Scan Link</button>
                </div>
            </div>

            <div id="fileMetaRow" class="hidden flex flex-col sm:flex-row items-stretch sm:items-center justify-between bg-cAcc1 p-6 border-[3px] border-cText shadow-hard-sm mt-2 transition-all gap-5 sm:gap-0">
                <div class="flex items-center gap-4 sm:gap-5 w-full sm:w-auto overflow-hidden">
                    <div class="text-4xl bg-cCard border-[2px] border-cText p-3 shadow-hard-sm shrink-0" id="metaIconContainer">
                        <span id="metaIconFile" aria-hidden="true">📄</span>
                        <span id="metaIconLink" class="hidden" aria-hidden="true">🔗</span>
                    </div>
                    <div class="min-w-0 flex-1 overflow-hidden">
                        <p id="selectedFileName" class="font-typewriter font-bold text-base sm:text-lg text-cText truncate w-full">timeline.xml</p>
                        <p id="selectedFileSize" class="text-xs sm:text-sm text-cText font-bold mt-1 uppercase tracking-wider">Ready for audit</p>
                    </div>
                </div>
                <div class="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                    <button id="clearSelectionBtn" class="w-full sm:w-auto bg-cCard text-cText font-bold px-4 py-4 sm:px-6 text-sm sm:text-base uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover transition-all whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-cText">Cancel</button>
                    <button id="runAuditBtn" class="w-full sm:w-auto bg-cAcc3 text-cCard font-bold px-6 py-4 sm:px-8 text-sm sm:text-base uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-cText">Initialize</button>
                </div>
            </div>

            <div id="progressContainer" class="hidden mt-2 space-y-6 sm:space-y-8 bg-cCard p-6 sm:p-8 border-[3px] border-cText shadow-hard-sm" role="status" aria-live="polite">
                <div class="space-y-2 sm:space-y-3">
                    <div class="flex justify-between text-xs sm:text-sm font-typewriter font-bold uppercase tracking-wider text-cText">
                        <span id="scanText" class="truncate pr-2">Pending safety check...</span>
                        <span id="scanPercent">0%</span>
                    </div>
                    <div class="w-full bg-cBg h-4 sm:h-6 border-[2px] sm:border-[3px] border-cText relative" role="progressbar" aria-valuemin="0" aria-valuemax="100" id="scanProgressContainer">
                        <div id="scanBar" class="bg-cAcc1 h-full w-0 progress-transition border-r-[2px] sm:border-r-[3px] border-cText"></div>
                    </div>
                </div>
                <div class="space-y-2 sm:space-y-3">
                    <div class="flex justify-between text-xs sm:text-sm font-typewriter font-bold uppercase tracking-wider text-cText">
                        <span id="detectText" class="truncate pr-2">Waiting for engine...</span>
                        <span id="detectPercent">0%</span>
                    </div>
                    <div class="w-full bg-cBg h-4 sm:h-6 border-[2px] sm:border-[3px] border-cText relative" role="progressbar" aria-valuemin="0" aria-valuemax="100" id="detectProgressContainer">
                        <div id="detectBar" class="bg-cAcc2 h-full w-0 progress-transition border-r-[2px] sm:border-r-[3px] border-cText"></div>
                    </div>
                </div>
            </div>
        </main>

        <section id="resultsDashboard" class="hidden bg-cCard border-[3px] sm:border-[4px] border-cText p-6 sm:p-12 shadow-hard mt-6 sm:mt-8 w-full transition-all duration-500 transform translate-y-4 opacity-0 mb-4 mr-2 sm:mr-3">
            <div class="flex flex-col md:flex-row md:justify-between md:items-end mb-6 sm:mb-10 border-b-[3px] sm:border-b-[4px] border-cText pb-6 gap-4 sm:gap-5">
                <div class="space-y-3 overflow-hidden w-full md:w-auto">
                    <div class="text-cText text-xs flex items-center gap-3 font-bold">
                        <span class="bg-cBg px-3 py-1.5 text-[10px] sm:text-[11px] font-typewriter tracking-widest uppercase border-[2px] border-cText shadow-hard-sm" id="dashFormat">Verified Format</span>
                        <span class="truncate">ANALYSIS COMPLETE</span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-bold tracking-tight text-cText truncate w-full font-typewriter uppercase" id="dashFileName">timeline.xml</h2>
                </div>
                <div class="w-full md:w-auto shrink-0 mt-4 md:mt-0">
                    <div class="flex items-center justify-center w-full md:w-auto gap-2 px-6 py-3 sm:py-4 text-xs sm:text-sm font-bold tracking-widest uppercase border-[3px] border-cText shadow-hard-sm" id="dashStatus">Processing...</div>
                </div>
            </div>
            <div id="geminiSummaryContainer" class="hidden mb-6 sm:mb-8 p-4 sm:p-6 bg-cBg/50 border-[2px] sm:border-[3px] border-cText shadow-hard-sm" aria-live="polite">
                <p id="geminiSummaryText" class="text-xs sm:text-sm font-medium text-cText leading-relaxed"></p>
            </div>
            <div class="space-y-6">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <h3 class="text-sm sm:text-base font-bold text-cText tracking-[0.1em] sm:tracking-[0.2em] uppercase flex items-center gap-3">
                        <span class="text-2xl" aria-hidden="true">📋</span> Compliance Log
                    </h3>
                    <button id="geminiSummaryBtn" class="w-full sm:w-auto bg-cText text-cBg px-4 py-3 sm:py-2 text-xs font-bold uppercase tracking-widest hover:bg-cAcc1 hover:text-cText border-[2px] sm:border-[3px] border-cText shadow-hard-sm transition-colors">✨ Generate Exec Summary</button>
                </div>
                <div class="w-full">
                    <table class="adaptive-table w-full text-left border-collapse" id="auditTable">
                        <thead>
                            <tr class="bg-cBg text-cText text-xs uppercase tracking-widest font-bold border-[3px] border-cText">
                                <th class="py-4 px-5 border-r-[3px] border-cText w-[15%]" scope="col">Timecode</th>
                                <th class="py-4 px-5 border-r-[3px] border-cText w-[20%]" scope="col">Class</th>
                                <th class="py-4 px-5 w-[65%]" scope="col">AI Insight</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm sm:text-base font-medium" id="auditTableBody"></tbody>
                    </table>
                </div>
            </div>
        </section>
    </div>

    <div id="guideModal" class="fixed inset-0 bg-cText/90 z-50 hidden flex items-center justify-center p-4 sm:p-6 opacity-0 transition-opacity duration-300" role="dialog" aria-modal="true" aria-label="Official User Documentation">
        <div class="bg-cCard border-[3px] sm:border-[4px] border-cText p-6 sm:p-12 shadow-hard max-w-3xl w-full max-h-[90vh] overflow-y-auto relative" id="guideModalContainer">
            <button id="closeGuideBtn" class="absolute top-3 right-5 sm:top-4 sm:right-5 text-3xl font-bold text-cText hover:text-cAcc3 transition-colors focus:outline-none p-2" aria-label="Close User Guide Modal">&times;</button>
            <div class="text-center mb-6 sm:mb-8 border-b-[3px] sm:border-b-[4px] border-cText pb-4 sm:pb-6 mt-4 sm:mt-0">
                <h2 class="text-2xl sm:text-4xl font-bold uppercase tracking-tight text-cText">DeepCut Protocol</h2>
                <p class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 uppercase tracking-widest font-bold">Official User Documentation</p>
            </div>
            <div class="space-y-8 sm:space-y-10 text-cText">
                <section>
                    <h3 class="inline-block bg-cAcc1 text-cText border-[2px] border-cText px-4 py-1.5 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase mb-4 shadow-hard-sm">Why DeepCut?</h3>
                    <div class="space-y-4">
                        <p class="font-medium leading-relaxed text-sm sm:text-base">DeepCut is designed to eliminate the costly human errors associated with manual cinematic auditing. Before media goes live to broadcast or streaming, it must pass rigorous standards.</p>
                        <p class="font-medium leading-relaxed text-sm sm:text-base">Our proprietary engine leverages advanced AI to instantly detect unauthorized copyrighted material, glaring continuity errors, and broadcast standards violations (such as profanity or explicit competitor brand mentions). With military-grade JWT encryption and a secure cloud architecture, your pre-release media remains strictly confidential.</p>
                    </div>
                </section>
                
                <section>
                    <h3 class="inline-block bg-cAcc2 text-cBg border-[2px] border-cText px-4 py-1.5 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase mb-4 shadow-hard-sm">Operating Procedure</h3>
                    <div class="space-y-4 text-sm sm:text-base font-medium leading-relaxed">
                        <ul class="list-none space-y-4">
                            <li class="flex items-start gap-3">
                                <span class="bg-cText text-cBg font-bold px-2 py-0.5 text-xs rounded-sm mt-0.5">1</span>
                                <div><strong class="font-bold text-cText">Input:</strong> Drag and drop your timeline file (XML) or paste a secure web link into the workspace. Supported formats include .xml, .fcpxml, .edl, and standard video streams (.mp4, .m4a).</div>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="bg-cText text-cBg font-bold px-2 py-0.5 text-xs rounded-sm mt-0.5">2</span>
                                <div><strong class="font-bold text-cText">Initialize:</strong> Click "Initialize" or "Scan Link" to send the media through our secure background processing pipeline. You can safely switch tabs while the engine is running.</div>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="bg-cText text-cBg font-bold px-2 py-0.5 text-xs rounded-sm mt-0.5">3</span>
                                <div><strong class="font-bold text-cText">Review:</strong> Examine the Compliance Log for detected anomalies, copyright warnings, or standards violations accurately mapped to their specific timecodes.</div>
                            </li>
                            <li class="flex items-start gap-3">
                                <span class="bg-cText text-cBg font-bold px-2 py-0.5 text-xs rounded-sm mt-0.5">4</span>
                                <div><strong class="font-bold text-cText">Resolve:</strong> Use the "✨ Suggest Fix" button on any flagged item to securely query our AI module for an instant, actionable post-production strategy to remedy the error.</div>
                            </li>
                        </ul>
                    </div>
                </section>

                <section>
                    <h3 class="inline-block bg-cAcc3 text-cCard border-[2px] border-cText px-4 py-1.5 text-xs sm:text-sm font-bold tracking-[0.2em] uppercase mb-4 shadow-hard-sm">The Vault Archive</h3>
                    <div class="space-y-4">
                        <p class="font-medium leading-relaxed text-sm sm:text-base">Every scan you initialize is securely tied to your operator profile. Access the <strong class="font-bold">Vault Archive</strong> by clicking the 📁 Vault button in the top navigation to review past compliance reports.</p>
                        <p class="font-medium leading-relaxed text-sm sm:text-base">All historical data is heavily encrypted using JSON Web Tokens (JWT). The backend enforces strict relational isolation, ensuring you will only ever see, load, and manage your own specific audit history.</p>
                    </div>
                </section>
            </div>
        </div>
    </div>

    <div id="changePassModal" class="fixed inset-0 bg-cText/90 z-50 hidden flex items-center justify-center p-4 sm:p-6 opacity-0 transition-opacity duration-300" role="dialog" aria-modal="true" aria-label="Change Access Code">
        <div class="bg-cCard border-[3px] sm:border-[4px] border-cText p-6 sm:p-10 shadow-hard max-w-lg w-full relative">
            <button id="closeChangePassBtn" class="absolute top-3 right-5 sm:top-4 sm:right-5 text-3xl font-bold text-cText hover:text-cAcc3 transition-colors focus:outline-none p-2" aria-label="Close Change Password Modal">&times;</button>
            <div class="text-center mb-6 sm:mb-8 border-b-[3px] sm:border-b-[4px] border-cText pb-4 sm:pb-6 mt-4 sm:mt-0">
                <h2 class="text-2xl sm:text-4xl font-bold uppercase tracking-tight text-cText">Update Code</h2>
                <p class="text-cSubtext text-xs sm:text-sm font-typewriter mt-2 uppercase tracking-widest font-bold">Secure Your Profile</p>
            </div>
            <div class="space-y-4">
                <div>
                    <label for="currentPass" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">Current Password / Temp Code</label>
                    <input type="password" id="currentPass" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <div>
                    <label for="newPass" class="block text-cText text-xs font-bold tracking-widest uppercase mb-1">New Password</label>
                    <input type="password" id="newPass" class="w-full bg-cBg/50 border-[2px] border-cText text-cText px-4 py-3 focus:outline-none focus:bg-cBg transition-colors text-sm font-typewriter font-bold shadow-hard-sm">
                </div>
                <button id="submitChangePassBtn" class="w-full bg-cAcc2 text-cBg font-bold px-6 py-4 uppercase tracking-widest border-[3px] border-cText shadow-hard shadow-hard-hover shadow-hard-active transition-all mt-4 text-sm sm:text-base">Update Access Code</button>
            </div>
        </div>
    </div>

    <script>
        // --- THEME & VAULT LOGIC ---
        const themes = ['default', 'fox', 'silver'];
        const themeLabels = ['🎨 Standard', '🦊 Fox Autumn', '🎞️ Silver Screen'];
        let currentThemeIndex = 0;
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        const vaultBtn = document.getElementById('vaultBtn');
        const vaultDrawer = document.getElementById('vaultDrawer');
        const closeVaultBtn = document.getElementById('closeVaultBtn');
        const vaultOverlay = document.getElementById('vaultOverlay');
        const vaultList = document.getElementById('vaultList');
        const vaultSortDropdown = document.getElementById('vaultSort');
        let vaultFocusCleanup = null;
        let authToken = null;
        let currentAudits = [];

        themeToggleBtn.addEventListener('click', () => {
            currentThemeIndex = (currentThemeIndex + 1) % themes.length;
            const selectedTheme = themes[currentThemeIndex];
            if (selectedTheme === 'default') document.body.removeAttribute('data-theme');
            else document.body.setAttribute('data-theme', selectedTheme);
            themeToggleBtn.textContent = themeLabels[currentThemeIndex];
        });

        function trapModalFocus(modalEl, closeBtnEl, triggerBtnEl) {
            const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
            const focusableContent = modalEl.querySelectorAll(focusableElements);
            const firstFocusableElement = focusableContent[0] || closeBtnEl;
            const lastFocusableElement = focusableContent[focusableContent.length - 1] || closeBtnEl;
            setTimeout(() => { firstFocusableElement.focus(); }, 100);
            const keyHandler = function(e) {
                if (e.key === 'Escape') { closeBtnEl.click(); return; }
                if (e.key === 'Tab') {
                    if (e.shiftKey) { if (document.activeElement === firstFocusableElement) { lastFocusableElement.focus(); e.preventDefault(); } }
                    else { if (document.activeElement === lastFocusableElement) { firstFocusableElement.focus(); e.preventDefault(); } }
                }
            };
            modalEl.addEventListener('keydown', keyHandler);
            return function() { modalEl.removeEventListener('keydown', keyHandler); setTimeout(() => { triggerBtnEl.focus(); }, 100); };
        }

        // --- GUIDE MODAL LOGIC ---
        const guideBtn = document.getElementById('guideBtn');
        const guideModal = document.getElementById('guideModal');
        const closeGuideBtn = document.getElementById('closeGuideBtn');
        let guideFocusCleanup = null;

        guideBtn.addEventListener('click', () => {
            guideModal.classList.remove('hidden');
            setTimeout(() => { guideModal.classList.remove('opacity-0'); }, 10);
            guideFocusCleanup = trapModalFocus(guideModal, closeGuideBtn, guideBtn);
        });

        const closeGuide = () => {
            guideModal.classList.add('opacity-0');
            setTimeout(() => { guideModal.classList.add('hidden'); }, 300);
            if (guideFocusCleanup) { guideFocusCleanup(); guideFocusCleanup = null; }
        };
        closeGuideBtn.addEventListener('click', closeGuide);
        guideModal.addEventListener('click', (e) => {
            if (e.target === guideModal) closeGuide();
        });


        // --- CHANGE PASSWORD MODAL LOGIC ---
        const changePassBtn = document.getElementById('changePassBtn');
        const changePassModal = document.getElementById('changePassModal');
        const closeChangePassBtn = document.getElementById('closeChangePassBtn');
        const submitChangePassBtn = document.getElementById('submitChangePassBtn');
        const currentPassInput = document.getElementById('currentPass');
        const newPassInput = document.getElementById('newPass');
        let changePassFocusCleanup = null;

        changePassBtn.addEventListener('click', () => {
            changePassModal.classList.remove('hidden');
            setTimeout(() => { changePassModal.classList.remove('opacity-0'); }, 10);
            changePassFocusCleanup = trapModalFocus(changePassModal, closeChangePassBtn, changePassBtn);
        });

        const closeChangePass = () => {
            changePassModal.classList.add('opacity-0');
            setTimeout(() => { 
                changePassModal.classList.add('hidden'); 
                currentPassInput.value = '';
                newPassInput.value = '';
            }, 300);
            if (changePassFocusCleanup) { changePassFocusCleanup(); changePassFocusCleanup = null; }
        };
        
        closeChangePassBtn.addEventListener('click', closeChangePass);
        changePassModal.addEventListener('click', (e) => {
            if (e.target === changePassModal) closeChangePass();
        });

        submitChangePassBtn.addEventListener('click', async () => {
            const curPass = currentPassInput.value;
            const nPass = newPassInput.value;
            
            if (!curPass || !nPass) {
                showCustomMsg("Please fill out both the current and new code fields.");
                return;
            }
            
            submitChangePassBtn.disabled = true;
            submitChangePassBtn.textContent = "UPDATING...";
            
            const formData = new URLSearchParams();
            formData.append('current_password', curPass);
            formData.append('new_password', nPass);
            
            try {
                // This hits the backend endpoint that verifies the old code before saving the new one
                const response = await fetch('https://deepcut-app.onrender.com/api/change-password', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: formData
                });
                
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "Update failed. Check your current access code.");
                
                showCustomMsg("Access code updated securely.", true);
                closeChangePass();
            } catch (err) {
                showCustomMsg(err.message || "Failed to update access code.");
            } finally {
                submitChangePassBtn.disabled = false;
                submitChangePassBtn.textContent = "UPDATE ACCESS CODE";
            }
        });


        vaultBtn.addEventListener('click', () => {
            loadHistory();
            vaultDrawer.classList.remove('-translate-x-full');
            vaultOverlay.classList.remove('hidden');
            setTimeout(() => { vaultOverlay.classList.add('opacity-100'); }, 10);
            vaultFocusCleanup = trapModalFocus(vaultDrawer, closeVaultBtn, vaultBtn);
        });

        const closeVault = () => {
            vaultDrawer.classList.add('-translate-x-full');
            vaultOverlay.classList.remove('opacity-100');
            setTimeout(() => { vaultOverlay.classList.add('hidden'); }, 300);
            if (vaultFocusCleanup) { vaultFocusCleanup(); vaultFocusCleanup = null; }
        };
        closeVaultBtn.addEventListener('click', closeVault);
        vaultOverlay.addEventListener('click', closeVault);

        // VAULT ARCHIVE RETRIEVAL & SORTING
        async function loadHistory() {
            if (!authToken) return;
            vaultList.innerHTML = `<p class="text-center text-cMuted text-xs font-typewriter uppercase mt-10 animate-pulse">Syncing Vault Registry...</p>`;
            try {
                const response = await fetch('https://deepcut-app.onrender.com/api/audits', { 
                    headers: { 'Authorization': `Bearer ${authToken}` },
                    cache: 'no-store' 
                });
                
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error("HTTP 404: Endpoint Missing. Your Render backend is likely running an old main.py file. Please deploy the updated backend code.");
                    }
                    throw new Error(`HTTP Error ${response.status}: ${response.statusText || 'Access Denied'}`);
                }
                
                currentAudits = await response.json();
                renderVaultList();
                
            } catch (err) { 
                const errorDetail = err.message || err.toString() || "Unknown network connection failure";
                vaultList.innerHTML = `
                    <div class="text-center p-5 bg-cBg/20 border-2 border-cAcc3 shadow-hard-sm space-y-3">
                        <span class="text-3xl block" aria-hidden="true">⚠️</span>
                        <h4 class="font-bold text-xs uppercase tracking-wider text-cAcc3 font-typewriter">Sync Failure</h4>
                        <p class="text-[10px] text-cMuted leading-relaxed font-typewriter break-all bg-cBg/30 p-2 border border-cText/10" id="vaultErrorDetails">${errorDetail}</p>
                        <p class="text-[11px] text-cSubtext font-medium leading-relaxed">This typically happens if the compliance server is cold-starting or offline. Give it a moment and try again.</p>
                        <button id="retryVaultBtn" class="w-full bg-cAcc3 text-cCard font-bold py-2 px-3 text-xs uppercase tracking-widest border-2 border-cText shadow-hard hover:opacity-90 transition-all focus:outline-none focus:ring-2 focus:ring-cText">
                            🔄 Retry Sync
                        </button>
                    </div>
                `;
                document.getElementById('retryVaultBtn').addEventListener('click', () => { loadHistory(); });
            }
        }
        
        function renderVaultList() {
            if (!currentAudits || currentAudits.length === 0) { 
                vaultList.innerHTML = `<p class="text-center text-cMuted text-xs font-typewriter uppercase mt-10">No past audits</p>`; 
                return; 
            }
            
            const sortMode = vaultSortDropdown.value;
            const sortedAudits = [...currentAudits].sort((a, b) => {
                if (sortMode === 'date-desc') {
                    return new Date(b.timestamp) - new Date(a.timestamp);
                } else if (sortMode === 'date-asc') {
                    return new Date(a.timestamp) - new Date(b.timestamp);
                } else if (sortMode === 'name-asc') {
                    return a.filename.localeCompare(b.filename);
                } else if (sortMode === 'errors-desc') {
                    const countA = a.flag_count || 0;
                    const countB = b.flag_count || 0;
                    return countB - countA;
                }
                return 0;
            });
            
            vaultList.innerHTML = '';
            sortedAudits.forEach(audit => {
                const card = document.createElement('button');
                card.className = "w-full text-left p-4 bg-cCard border-[2px] border-cText shadow-hard-sm cursor-pointer hover:bg-cBg/20 transition-all focus:outline-none focus:ring-2 focus:ring-cAcc1 mb-3 block";
                
                let flagCount = audit.flag_count || 0;
                let statusLabel = audit.status === "Flagged" ? `🚩 ${flagCount} Flags` : `🌟 Clean`;
                if (audit.status === "Error") statusLabel = "⚠️ Error";
                if (audit.status === "Running") statusLabel = "⏳ Scanning";

                card.innerHTML = `
                    <p class="font-typewriter font-bold text-xs truncate text-cText">${audit.filename}</p>
                    <p class="text-[9px] font-typewriter text-cMuted mt-1">${audit.timestamp}</p>
                    <div class="flex justify-between items-center mt-3">
                        <span class="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 border border-cText bg-cBg/40">${audit.format}</span>
                        <span class="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 border ${audit.status === 'Flagged' ? 'border-cAcc3 text-cAcc3' : 'border-cSuccess text-cSuccess'}">${statusLabel}</span>
                    </div>
                `;
                card.addEventListener('click', () => { loadSingleAudit(audit.id); closeVault(); });
                vaultList.appendChild(card);
            });
        }
        
        vaultSortDropdown.addEventListener('change', renderVaultList);

        async function loadSingleAudit(auditId) {
            try {
                // Fetching detail structure verified by the token security layer
                const response = await fetch(`https://deepcut-app.onrender.com/api/audits/${auditId}`, { 
                    headers: { 'Authorization': `Bearer ${authToken}` },
                    cache: 'no-store'
                });
                const data = await response.json();
                populateAndRevealDashboard(data);
            } catch (err) { 
                showCustomMsg("Failed to pull log."); 
            }
        }

        // --- AUTH & CORE APP LOGIC ---
        const loginScreen = document.getElementById('loginScreen');
        const registerScreen = document.getElementById('registerScreen');
        const forgotPasswordScreen = document.getElementById('forgotPasswordScreen');
        
        const showRegisterBtn = document.getElementById('showRegisterBtn');
        const showForgotBtn = document.getElementById('showForgotBtn');
        const showLoginBtn = document.getElementById('showLoginBtn');
        const backToLoginFromForgotBtn = document.getElementById('backToLoginFromForgotBtn');
        
        const loginBtn = document.getElementById('loginBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        const sendResetBtn = document.getElementById('sendResetBtn');
        const resetEmailInput = document.getElementById('resetEmail');

        const regName = document.getElementById('regName');
        const regUsername = document.getElementById('regUsername');
        const regEmail = document.getElementById('regEmail');
        const regPassword = document.getElementById('regPassword');
        const registerBtn = document.getElementById('registerBtn');
        const reqLength = document.getElementById('reqLength');
        const reqUpper = document.getElementById('reqUpper');
        const reqSpecial = document.getElementById('reqSpecial');

        // Navigation Transitions
        showRegisterBtn.addEventListener('click', () => {
            loginScreen.classList.add('fade-hidden');
            setTimeout(() => {
                loginScreen.style.position = 'absolute'; 
                registerScreen.style.position = 'relative';
                registerScreen.classList.remove('fade-hidden'); 
                regName.focus();
            }, 500);
        });
        
        showForgotBtn.addEventListener('click', () => {
            loginScreen.classList.add('fade-hidden');
            setTimeout(() => {
                loginScreen.style.position = 'absolute'; 
                forgotPasswordScreen.style.position = 'relative';
                forgotPasswordScreen.classList.remove('fade-hidden'); 
                resetEmailInput.focus();
            }, 500);
        });

        const showLoginFromAnywhere = () => {
            registerScreen.classList.add('fade-hidden');
            forgotPasswordScreen.classList.add('fade-hidden');
            setTimeout(() => {
                registerScreen.style.position = 'absolute'; 
                forgotPasswordScreen.style.position = 'absolute';
                loginScreen.style.position = 'relative';
                loginScreen.classList.remove('fade-hidden'); 
                document.getElementById('loginUsername').focus();
            }, 500);
        };

        showLoginBtn.addEventListener('click', showLoginFromAnywhere);
        backToLoginFromForgotBtn.addEventListener('click', showLoginFromAnywhere);

        // Password Reset Request Handler
        sendResetBtn.addEventListener('click', async () => {
            const email = resetEmailInput.value.trim();
            if (!email || !email.includes('@')) {
                showCustomMsg("Please enter a valid email address.");
                return;
            }
            
            sendResetBtn.disabled = true;
            sendResetBtn.textContent = "SENDING...";
            
            const formData = new URLSearchParams();
            formData.append('email', email);
            
            try {
                const response = await fetch('https://deepcut-app.onrender.com/api/forgot-password', { 
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, 
                    body: formData 
                });
                
                if (!response.ok) throw new Error();
                
                showCustomMsg("If an account matches that email, a reset link has been dispatched.", true);
                resetEmailInput.value = '';
                showLoginFromAnywhere();
            } catch (error) {
                // Even on error (like endpoint missing), we show a generic message for security
                showCustomMsg("If an account matches that email, a reset link has been dispatched.", true);
                showLoginFromAnywhere();
            } finally {
                sendResetBtn.disabled = false;
                sendResetBtn.textContent = "SEND RESET LINK";
            }
        });

        function updateRequirement(element, isMet) {
            if (isMet) {
                element.classList.remove('req-unmet'); element.classList.add('req-met');
                element.querySelector('.status-icon').textContent = '●';
            } else {
                element.classList.remove('req-met'); element.classList.add('req-unmet');
                element.querySelector('.status-icon').textContent = '○';
            }
        }

        regPassword.addEventListener('input', (e) => {
            const val = e.target.value;
            const hasLength = val.length >= 12;
            const hasUpper = /[A-Z]/.test(val);
            const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(val);

            updateRequirement(reqLength, hasLength);
            updateRequirement(reqUpper, hasUpper);
            updateRequirement(reqSpecial, hasSpecial);

            const isFormValid = regName.value.trim() && regUsername.value.trim() && regEmail.value.includes('@') && hasLength && hasUpper && hasSpecial;
            registerBtn.disabled = !isFormValid;
        });

        [regName, regUsername, regEmail].forEach(input => {
            input.addEventListener('input', () => regPassword.dispatchEvent(new Event('input')));
            input.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !registerBtn.disabled) registerBtn.click(); });
        });
        
        regPassword.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !registerBtn.disabled) registerBtn.click(); });

        registerBtn.addEventListener('click', async () => {
            registerBtn.disabled = true; registerBtn.textContent = "CREATING...";
            const formData = new URLSearchParams();
            formData.append('name', regName.value.trim()); formData.append('username', regUsername.value.trim());
            formData.append('email', regEmail.value.trim()); formData.append('password', regPassword.value);

            try {
                const response = await fetch('https://deepcut-app.onrender.com/api/register', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || "Registration failed");
                showCustomMsg("Operator registered successfully. You may now log in.", true);
                regName.value = ''; regUsername.value = ''; regEmail.value = ''; regPassword.value = '';
                showLoginFromAnywhere();
            } catch (error) { showCustomMsg(error.message); } 
            finally { registerBtn.textContent = "CREATE OPERATOR"; regPassword.dispatchEvent(new Event('input')); }
        });
        
        loginBtn.addEventListener('click', async () => {
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;
            const formData = new URLSearchParams();
            formData.append('username', username); formData.append('password', password);
            try {
                const response = await fetch('https://deepcut-app.onrender.com/api/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
                if (!response.ok) throw new Error();
                const data = await response.json();
                authToken = data.access_token;
                document.getElementById('displayUsername').textContent = data.username || username;
                document.getElementById('authContainer').classList.add('hidden');
                document.getElementById('appScreen').classList.remove('hidden');
                setTimeout(() => document.getElementById('appScreen').classList.remove('opacity-0'), 50);
                loadHistory();
            } catch (e) { showCustomMsg("Login failed. Check your identification parameters."); }
        });

        logoutBtn.addEventListener('click', () => { window.location.reload(); });

        const fileInput = document.getElementById('fileInput');
        const uploadZone = document.getElementById('uploadZone');
        const fileMetaRow = document.getElementById('fileMetaRow');
        const inputWorkspace = document.getElementById('inputWorkspace');
        let selectedFiles = [];
        let submittedUrl = null;

        fileInput.addEventListener('change', (e) => { if(e.target.files.length) handleFile(e.target.files[0]); });
        
        document.getElementById('clearSelectionBtn').addEventListener('click', () => {
            fileInput.value = ''; document.getElementById('urlInput').value = '';
            selectedFiles = []; submittedUrl = null;
            inputWorkspace.classList.remove('hidden'); fileMetaRow.classList.add('hidden');
        });

        function handleFile(file) {
            selectedFiles = [file]; submittedUrl = null;
            document.getElementById('selectedFileName').textContent = file.name;
            document.getElementById('selectedFileSize').textContent = (file.size / 1024).toFixed(1) + ' KB';
            document.getElementById('metaIconLink').classList.add('hidden'); document.getElementById('metaIconFile').classList.remove('hidden');
            inputWorkspace.classList.add('hidden'); fileMetaRow.classList.remove('hidden');
        }

        document.getElementById('runUrlBtn').addEventListener('click', () => {
            const urlInput = document.getElementById('urlInput');
            if (!urlInput.value.trim()) return;
            selectedFiles = []; submittedUrl = urlInput.value.trim();
            document.getElementById('metaIconFile').classList.add('hidden'); document.getElementById('metaIconLink').classList.remove('hidden');
            document.getElementById('selectedFileName').textContent = submittedUrl;
            document.getElementById('selectedFileSize').textContent = "Web Stream";
            inputWorkspace.classList.add('hidden'); fileMetaRow.classList.remove('hidden');
        });

        let pollInterval = null;
        let ws = null;

        function stopMonitoring() {
            if (ws) { try { ws.close(); } catch(e){} ws = null; }
            if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
        }

        function handleProgressUpdate(stage, progress, message) {
            const barId = stage === 'scan' ? 'scanBar' : 'detectBar';
            const percentId = stage === 'scan' ? 'scanPercent' : 'detectPercent';
            const textId = stage === 'scan' ? 'scanText' : 'detectText';
            const progressContainerId = stage === 'scan' ? 'scanProgressContainer' : 'detectProgressContainer';
            
            document.getElementById(barId).style.width = progress + '%';
            document.getElementById(percentId).textContent = progress + '%';
            document.getElementById(textId).textContent = message;
            document.getElementById(progressContainerId).setAttribute('aria-valuenow', progress);
        }

        document.getElementById('runAuditBtn').addEventListener('click', async () => {
            if (selectedFiles.length === 0 && !submittedUrl) return;
            if (!authToken) { showCustomMsg("Missing authorization token."); return; }

            fileMetaRow.classList.add('hidden');
            document.getElementById('progressContainer').classList.remove('hidden');
            
            ['scanBar', 'detectBar'].forEach(id => document.getElementById(id).style.width = '0%');
            ['scanPercent', 'detectPercent'].forEach(id => document.getElementById(id).textContent = '0%');
            document.getElementById('scanText').textContent = "INITIALIZING SECURE UPLOAD...";
            document.getElementById('detectText').textContent = "WAITING FOR ENGINE...";

            stopMonitoring(); 

            try {
                const formData = new FormData();
                if (selectedFiles.length > 0) formData.append('file', selectedFiles[0]);
                else formData.append('video_url', submittedUrl);

                const response = await fetch('https://deepcut-app.onrender.com/api/audit/start', { method: 'POST', headers: { 'Authorization': `Bearer ${authToken}` }, body: formData });
                if (!response.ok) throw new Error("Server rejected audit request.");
                const { task_id } = await response.json();

                let usingPollingFallback = false;

                function startPollingFallback() {
                    if (usingPollingFallback) return;
                    usingPollingFallback = true;
                    
                    pollInterval = setInterval(async () => {
                        try {
                            const res = await fetch(`https://deepcut-app.onrender.com/api/audit/status/${task_id}`, { headers: { 'Authorization': `Bearer ${authToken}` } });
                            if (!res.ok) return;
                            const data = await res.json();
                            
                            if (data.status === 'running') {
                                handleProgressUpdate(data.stage, data.progress, data.message);
                            } else if (data.status === 'complete') {
                                stopMonitoring(); populateAndRevealDashboard(data.result); loadHistory(); 
                            } else if (data.status === 'error') {
                                stopMonitoring(); showCustomMsg(data.message || "An error occurred during polling.");
                            }
                        } catch (err) { console.error("Polling error:", err); }
                    }, 1500);
                }

                try {
                    ws = new WebSocket(`wss://deepcut-app.onrender.com/ws/audit/${task_id}`);
                    const wsTimeout = setTimeout(() => { if (ws && ws.readyState !== WebSocket.OPEN) startPollingFallback(); }, 2500);

                    ws.onopen = () => clearTimeout(wsTimeout);
                    ws.onmessage = (event) => {
                        const payload = JSON.parse(event.data);
                        if (payload.status === 'progress') {
                            handleProgressUpdate(payload.stage, payload.progress, payload.message);
                        } else if (payload.status === 'complete') {
                            stopMonitoring(); populateAndRevealDashboard(payload.result); loadHistory(); 
                        } else if (payload.status === 'error') {
                            stopMonitoring(); showCustomMsg(payload.message || "Audit failed.");
                        }
                    };
                    ws.onerror = () => { clearTimeout(wsTimeout); startPollingFallback(); };
                    ws.onclose = () => { clearTimeout(wsTimeout); startPollingFallback(); };
                } catch (wsSetupError) { startPollingFallback(); }
            } catch (error) {
                document.getElementById('scanText').textContent = "ERROR."; document.getElementById('detectText').textContent = "FAILED.";
                showCustomMsg(error.message || "An unexpected error occurred during processing.");
                setTimeout(() => { document.getElementById('progressContainer').classList.add('hidden'); inputWorkspace.classList.remove('hidden'); }, 3000);
            }
        });

        // SECURE BACKEND AI AGENT TRIGGERS
        const geminiSummaryBtn = document.getElementById('geminiSummaryBtn');

        geminiSummaryBtn.addEventListener('click', async (e) => {
            if (!authToken) return;
            const btn = e.target; btn.disabled = true; btn.textContent = "✨ Analyzing...";
            document.getElementById('geminiSummaryContainer').classList.remove('hidden');
            document.getElementById('geminiSummaryText').textContent = "AI drafting executive summary...";
            
            let reportData = ""; 
            document.querySelectorAll('#auditTableBody tr').forEach(row => { reportData += row.innerText + "\n"; });

            try {
                const res = await fetch('https://deepcut-app.onrender.com/api/ai/summary', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                    body: JSON.stringify({ report: reportData })
                });
                const data = await res.json();
                document.getElementById('geminiSummaryText').innerHTML = `<span class="font-bold text-[11px] sm:text-xs text-cAcc2 block mb-1.5 uppercase tracking-widest">✨ AI Executive Summary:</span> ${data.text}`;
            } catch (err) {
                document.getElementById('geminiSummaryText').textContent = "Error generating summary profile.";
            } finally {
                btn.textContent = "✨ Summary Generated";
            }
        });

        function populateAndRevealDashboard(data) {
            document.getElementById('dashFileName').textContent = data.filename;
            document.getElementById('dashStatus').textContent = data.anomalies && data.anomalies.length ? `🚩 ${data.anomalies.length} Flags` : "🌟 Clean";
            const tableBody = document.getElementById('auditTableBody');
            tableBody.innerHTML = '';
            
            geminiSummaryBtn.disabled = false; geminiSummaryBtn.textContent = "✨ Generate Exec Summary";
            document.getElementById('geminiSummaryContainer').classList.add('hidden');

            if (data.status === "error" || data.error) {
                tableBody.innerHTML = `<tr><td colspan="3" class="p-6 text-center text-cAcc3 font-bold text-sm">${data.error || "Compliance Engine Error."}</td></tr>`;
            } else if (data.anomalies && data.anomalies.length > 0) {
                data.anomalies.forEach(a => {
                    tableBody.innerHTML += `
                        <tr class="border-b-[2px] sm:border-b-[3px] border-cText block sm:table-row">
                            <td class="p-4 sm:p-6 font-bold border-b sm:border-b-0 sm:border-r-[3px] border-cText block sm:table-cell w-full sm:w-auto" data-label="Timecode">${a.timecode}</td>
                            <td class="p-4 sm:p-6 border-b sm:border-b-0 sm:border-r-[3px] border-cText block sm:table-cell w-full sm:w-auto" data-label="Class"><span class="bg-cAcc3 text-cCard px-2 py-1 text-[9px] sm:text-xs font-bold">${a.type}</span></td>
                            <td class="p-4 sm:p-6 block sm:table-cell w-full sm:w-auto" data-label="AI Insight">
                                <span class="block leading-relaxed text-sm">${a.description}</span>
                                <div class="mt-4">
                                    <button class="btn-sugerir w-full sm:w-auto bg-cText text-cBg px-4 py-3 sm:px-3 sm:py-2 text-xs sm:text-[10px] font-bold hover:bg-cAcc2 uppercase tracking-widest transition-colors focus:outline-none focus:ring-2 focus:ring-cAcc1" data-type="${a.type}" data-desc="${a.description}">✨ Suggest Fix</button>
                                    <div class="sugerencia-out hidden mt-3 sm:mt-3 p-4 bg-cCard border-[2px] border-dashed border-cText text-sm whitespace-normal leading-relaxed"></div>
                                </div>
                            </td>
                        </tr>`;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="3" class="p-8 text-center font-bold text-cSubtext text-sm sm:text-base">No compliance violations or anomalies detected.</td></tr>`;
            }

            document.querySelectorAll('.btn-sugerir').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!authToken) return;
                    const t = e.target; t.disabled = true; t.textContent = "✨ Processing...";
                    const out = t.nextElementSibling; out.classList.remove('hidden'); out.textContent = "Generating strategy...";
                    
                    try {
                        const res = await fetch('https://deepcut-app.onrender.com/api/ai/suggest', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
                            body: JSON.stringify({ type: t.getAttribute('data-type'), description: t.getAttribute('data-desc') })
                        });
                        const context = await res.json();
                        t.style.display = 'none'; 
                        out.innerHTML = `<span class="font-bold text-cAcc2 text-[10px] sm:text-[11px] block mb-2 uppercase tracking-widest">✨ Recommended Strategy:</span> ${context.text}`;
                    } catch (err) {
                        out.textContent = "Error communicating with secure broker.";
                        t.disabled = false; t.textContent = "✨ Suggest Fix";
                    }
                });
            });

            document.getElementById('progressContainer').classList.add('hidden'); inputWorkspace.classList.remove('hidden'); 
            const d = document.getElementById('resultsDashboard'); d.classList.remove('hidden');
            setTimeout(() => { d.classList.remove('opacity-0', 'translate-y-4'); d.scrollIntoView({ behavior: 'smooth' }); }, 50);

            const announcement = document.createElement('div');
            announcement.className = 'sr-only'; announcement.setAttribute('role', 'alert');
            announcement.textContent = "DeepCut Engine Audit complete. Results dashboard is now active.";
            document.body.appendChild(announcement);
            setTimeout(() => { announcement.remove(); }, 2000);
        }

        function showCustomMsg(msg, isSuccess = false) {
            const colorClass = isSuccess ? 'bg-cSuccess' : 'bg-cAcc3';
            const borderClass = isSuccess ? 'border-cSuccess' : 'border-cAcc3';
            const icon = isSuccess ? '✅' : '⚠️';
            const title = isSuccess ? 'SUCCESS' : 'SYSTEM NOTIFICATION';
            const modal = document.createElement('div');
            modal.className = "fixed inset-0 bg-cText/90 z-[100] flex items-center justify-center p-4 px-6 transition-colors duration-300";

            modal.innerHTML = `
                <div class="bg-cCard border-[3px] sm:border-[4px] ${borderClass} p-5 sm:p-8 shadow-hard max-w-sm w-full text-center mb-2 mr-2" role="dialog" aria-modal="true" aria-labelledby="notificationTitle" id="customMsgModal">
                    <span class="text-4xl sm:text-5xl mb-4 sm:mb-5 block" aria-hidden="true">${icon}</span>
                    <h3 id="notificationTitle" class="text-cText font-bold uppercase tracking-widest mb-3 sm:mb-4 text-sm sm:text-base">${title}</h3>
                    <p class="text-cSubtext text-xs sm:text-sm font-medium mb-6 sm:mb-8">${msg}</p>
                    <button class="${colorClass} text-cCard font-bold px-6 py-3 sm:px-8 sm:py-3 text-xs sm:text-sm uppercase tracking-widest border-[2px] sm:border-[3px] border-cText hover:opacity-80 transition-opacity w-full focus:outline-none focus:ring-2 focus:ring-cText" id="msgAcknowledgeBtn">Acknowledged</button>
                </div>
            `;
            document.body.appendChild(modal);
            const activeBtn = document.activeElement;
            const cleanup = trapModalFocus(modal, document.getElementById('msgAcknowledgeBtn'), activeBtn);
            document.getElementById('msgAcknowledgeBtn').addEventListener('click', () => { cleanup(); modal.remove(); });
        }
    </script>
</body>
</html>
