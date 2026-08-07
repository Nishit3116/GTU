// ── Global State ──
let currentSubjectsList = [];
let quickSearchDebounceTimer;
let activeSubjectIndex = null;
let activeDownloadType = null;

// ── Page Initialization ──
document.addEventListener("DOMContentLoaded", () => {
    // Initialize console logs
    appendConsoleLog("GTU Academic Engine V2 Web Client online.", "system");
    appendConsoleLog("Playwright scraper daemon ready for live queries.", "info");

    fetchStats();
    loadCourses();
    loadSettings();
    startTypewriter();
    startPlaceholderTypewriter();
    initSuggestionChips();

    // Cascading Dropdown Listeners
    document.getElementById("course-select").addEventListener("change", handleCourseChange);
    document.getElementById("branch-select").addEventListener("change", handleBranchChange);
    document.getElementById("sem-select").addEventListener("change", handleSemesterChange);

    // Quick Search Listeners
    document.getElementById("quick-search").addEventListener("input", handleQuickSearchInput);
    document.getElementById("quick-search").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            performQuickSearch();
        }
    });
    document.getElementById("quick-search-btn").addEventListener("click", performQuickSearch);
    document.addEventListener("click", handleDocumentClick);
});

// ── Console Log Engine ──
function appendConsoleLog(message, type = "info") {
    const timeStr = new Date().toLocaleTimeString();
    console.log(`[${timeStr}] [${type.toUpperCase()}] ${message}`);
}


// ── Typewriter Engine ──

const TYPEWRITER_PHRASES = [
    "Automated syllabus crawling & unified PYQ pipelines",
    "Live cascading GTU portal queries — no manual codes",
    "On-demand PDF merge with custom year range & sort order",
    "Optimised Playwright scraping — results in 2 to 4 seconds",
    "Local-first JSON cache with instant fuzzy subject search",
    "Glassmorphic dark-mode dashboard, built for engineers",
];

function startTypewriter() {
    const el = document.getElementById("typewriter-text");
    if (!el) return;

    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;

    const TYPE_SPEED   = 40;   // ms per character when typing
    const DELETE_SPEED = 20;   // ms per character when deleting
    const HOLD_DELAY   = 2400; // ms to hold a complete phrase
    const START_DELAY  = 200;  // ms pause before starting to delete

    function tick() {
        const phrase = TYPEWRITER_PHRASES[phraseIndex];

        if (!isDeleting) {
            // Typing forward
            el.textContent = phrase.slice(0, charIndex + 1);
            charIndex++;

            if (charIndex === phrase.length) {
                // Phrase fully typed — hold, then start deleting
                isDeleting = true;
                setTimeout(tick, HOLD_DELAY);
                return;
            }
            setTimeout(tick, TYPE_SPEED);
        } else {
            // Deleting backward
            el.textContent = phrase.slice(0, charIndex - 1);
            charIndex--;

            if (charIndex === 0) {
                // Fully deleted — move to next phrase
                isDeleting = false;
                phraseIndex = (phraseIndex + 1) % TYPEWRITER_PHRASES.length;
                setTimeout(tick, START_DELAY);
                return;
            }
            setTimeout(tick, DELETE_SPEED);
        }
    }

    tick();
}

// ── Placeholder Typewriter Engine ──
const PLACEHOLDER_EXAMPLES = [
    "Ask AI Copilot... (e.g. 'BE Computer sem 7')",
    "Ask AI Copilot... (e.g. 'Distributed Systems 3170719')",
    "Ask AI Copilot... (e.g. 'ME Mechanical sem 1')",
    "Ask AI Copilot... (e.g. '3130703 Database')",
    "Search subjects... (e.g. 'Cloud Computing')",
    "Ask AI Copilot... (e.g. 'Applied Science sem 5')"
];

function startPlaceholderTypewriter() {
    const input = document.getElementById("quick-search");
    if (!input) return;

    let index = 0;
    let charIndex = 0;
    let isDeleting = false;
    let currentText = "";

    function tick() {
        const fullText = PLACEHOLDER_EXAMPLES[index];

        if (!isDeleting) {
            currentText = fullText.slice(0, charIndex + 1);
            input.setAttribute("placeholder", currentText);
            charIndex++;

            if (charIndex === fullText.length) {
                isDeleting = true;
                setTimeout(tick, 3000);
                return;
            }
            setTimeout(tick, 35);
        } else {
            currentText = fullText.slice(0, charIndex - 1);
            input.setAttribute("placeholder", currentText);
            charIndex--;

            if (charIndex === 0) {
                isDeleting = false;
                index = (index + 1) % PLACEHOLDER_EXAMPLES.length;
                setTimeout(tick, 300);
                return;
            }
            setTimeout(tick, 15);
        }
    }

    tick();
}

// ── Suggestions Chips Engine ──
const SUGGESTION_CHIPS = [
    "BE Computer sem 7",
    "Distributed Systems 3170719",
    "3130703 Database",
    "ME Mechanical sem 1",
    "Cloud Computing"
];

function initSuggestionChips() {
    const container = document.getElementById("search-suggestions");
    if (!container) return;

    container.innerHTML = `<span class="suggestion-label">Try asking:</span>`;

    SUGGESTION_CHIPS.forEach(text => {
        const chip = document.createElement("button");
        chip.className = "suggestion-chip";
        chip.innerText = text;
        chip.addEventListener("click", () => {
            applySuggestion(text);
        });
        container.appendChild(chip);
    });
}

function applySuggestion(text) {
    const input = document.getElementById("quick-search");
    if (!input) return;
    input.value = text;
    appendConsoleLog(`[SUGGESTION] Adopted suggestion: "${text}"`, "info");
    performQuickSearch();
}

// ── API Fetchers ──

async function apiGet(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Request failed");
        }
        return await response.json();
    } catch (e) {
        showToast(e.message, "error");
        console.error(e);
        return null;
    }
}

async function apiPost(endpoint, body) {
    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Post request failed");
        }
        return await response.json();
    } catch (e) {
        showToast(e.message, "error");
        console.error(e);
        return null;
    }
}

// ── Loader functions ──

async function fetchStats() {
    const stats = await apiGet("/api/stats");
    if (stats && stats.exists) {
        document.getElementById("stat-subjects").innerText = stats.total_subjects;
        document.getElementById("stat-courses").innerText = stats.courses;
        document.getElementById("cache-last-updated").innerText = `Cache active. Last updated: ${stats.collected_at.slice(0, 10)}`;
        appendConsoleLog(`Local Cache: loaded ${stats.total_subjects} subjects across ${stats.courses} courses.`, "success");
    } else {
        document.getElementById("stat-subjects").innerText = "0";
        document.getElementById("stat-courses").innerText = "0";
        document.getElementById("cache-last-updated").innerText = "No cache data. Dynamic scraping active.";
        appendConsoleLog("No local cache registry file detected.", "info");
    }
}

async function loadCourses() {
    const select = document.getElementById("course-select");
    const courses = await apiGet("/api/courses");
    if (!courses) return;

    courses.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.innerText = `${c.name} (${c.id})`;
        select.appendChild(opt);
    });
    appendConsoleLog(`Loaded ${courses.length} default GTU courses/programs.`, "info");
}

// ── Cascading Handlers ──

async function handleCourseChange() {
    const courseId = this.value;
    const branchSelect = document.getElementById("branch-select");
    const semSelect = document.getElementById("sem-select");
    const yearSelect = document.getElementById("year-select");
    const electiveSelect = document.getElementById("elective-select");

    // Reset dependents
    resetSelect(branchSelect, "Select Branch");
    resetSelect(semSelect, "Select Semester");
    resetSelect(yearSelect, "Select Academic Year");
    resetSelect(electiveSelect, "Select Elective / Non-Elective");
    branchSelect.disabled = true;
    semSelect.disabled = true;
    yearSelect.disabled = true;
    electiveSelect.disabled = true;

    if (!courseId) return;

    appendConsoleLog(`Selecting course [${courseId}] - scraping available branches...`, "info");
    const branches = await apiGet(`/api/branches?course=${courseId}`);
    if (!branches) return;

    branches.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b.id;
        opt.innerText = b.name.startsWith(b.id) ? b.name : `${b.id} - ${b.name}`;
        branchSelect.appendChild(opt);
    });
    branchSelect.disabled = false;
    appendConsoleLog(`Found and loaded ${branches.length} branches for course [${courseId}].`, "success");
}

async function handleBranchChange() {
    const courseSelect = document.getElementById("course-select");
    const courseId = courseSelect.value;
    const branchId = this.value;
    const semSelect = document.getElementById("sem-select");
    const yearSelect = document.getElementById("year-select");
    const electiveSelect = document.getElementById("elective-select");

    resetSelect(semSelect, "Select Semester");
    resetSelect(yearSelect, "Select Academic Year");
    resetSelect(electiveSelect, "Select Elective / Non-Elective");
    semSelect.disabled = true;
    yearSelect.disabled = true;
    electiveSelect.disabled = true;

    if (!branchId) return;

    appendConsoleLog(`Branch [${branchId}] active. Fetching semesters and years...`, "info");
    // Load semesters and years concurrently
    const [sems, years] = await Promise.all([
        apiGet(`/api/semesters?course=${courseId}&branch=${branchId}`),
        apiGet(`/api/years?course=${courseId}&branch=${branchId}`)
    ]);

    if (sems) {
        sems.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.value;
            opt.innerText = s.text;
            semSelect.appendChild(opt);
        });
        semSelect.disabled = false;
    }

    if (years) {
        years.forEach(y => {
            const opt = document.createElement("option");
            opt.value = y;
            opt.innerText = y;
            yearSelect.appendChild(opt);
        });
        yearSelect.disabled = false;
    }
    appendConsoleLog(`Loaded semester schemes and effective academic years.`, "success");
}

async function handleSemesterChange() {
    const courseId = document.getElementById("course-select").value;
    const branchId = document.getElementById("branch-select").value;
    const sem = this.value;
    const electiveSelect = document.getElementById("elective-select");

    resetSelect(electiveSelect, "All (Elective & Non-Elective)");
    electiveSelect.disabled = true;

    if (!sem) return;

    // Enable it immediately to allow selecting "All"
    electiveSelect.disabled = false;

    appendConsoleLog(`Semester [${sem}] selected. Querying elective divisions...`, "info");
    const electives = await apiGet(`/api/electives?course=${courseId}&branch=${branchId}&sem=${sem}`);
    if (electives) {
        // Clear and keep the "All" default
        resetSelect(electiveSelect, "All (Elective & Non-Elective)");
        electives.forEach(e => {
            const opt = document.createElement("option");
            opt.value = e;
            opt.innerText = e.replace("_", "-");
            electiveSelect.appendChild(opt);
        });
        appendConsoleLog(`Loaded elective types: [${electives.join(", ")}].`, "success");
    }
}

function resetSelect(selectEl, defaultText) {
    selectEl.innerHTML = `<option value="">${defaultText}</option>`;
}

// ── Search & Results Table ──

async function searchSubjects() {
    const course = document.getElementById("course-select").value;
    const branch = document.getElementById("branch-select").value;
    const sem = document.getElementById("sem-select").value;
    const year = document.getElementById("year-select").value;
    const elective = document.getElementById("elective-select").value;
    const btn = document.getElementById("search-btn");
    const spinner = document.getElementById("search-spinner");

    if (!course || !branch || !sem) return;

    btn.disabled = true;
    spinner.classList.remove("hidden");

    appendConsoleLog(`[SCRAPE] Launching Playwright browser connection for Course=${course}, Branch=${branch}, Sem=${sem}...`, "system");
    const queryStr = `/api/subjects?course=${course}&branch=${branch}&sem=${sem}&year=${year}&elective=${elective}&live=true`;
    const subjects = await apiGet(queryStr);

    btn.disabled = false;
    spinner.classList.add("hidden");

    if (subjects) {
        appendConsoleLog(`[SCRAPE] Scrape completed. Found ${subjects.length} subjects.`, "success");
        displayResults(subjects, `Subjects Scraped (${course} / Branch ${branch} / Sem ${sem})`);
        fetchStats(); // Update stat counts if caching dynamic data
    } else {
        appendConsoleLog(`[SCRAPE] Live query failed or timed out. Check connection.`, "error");
    }
}

function displayResults(subjects, titleText) {
    currentSubjectsList = subjects;
    const resultsCard = document.getElementById("results-card");
    const resultsTitle = document.getElementById("results-title");
    const resultsCount = document.getElementById("results-count");
    const tbody = document.getElementById("subjects-tbody");

    resultsTitle.innerText = titleText;
    resultsCount.innerText = subjects.length;
    tbody.innerHTML = "";

    if (subjects.length === 0) {
        const msg = "No subjects found for this selection. Try selecting a different elective or academic year.";
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">${msg}</td></tr>`;
    } else {
        subjects.forEach((s, index) => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            tr.setAttribute("onclick", `toggleDetailsFromRow(event, this, ${index})`);
            tr.innerHTML = `
                <td>
                    <button class="expand-btn" onclick="event.stopPropagation(); toggleDetails(this, ${index});">▶</button>
                </td>
                <td><span class="sub-cell-title" style="color: hsl(250, 90%, 75%);">${s.subject_code}</span></td>
                <td>${s.branch}</td>
                <td>${s.academic_year || "June 2021"}</td>
                <td><span class="sub-cell-title">${s.subject_name}</span></td>
                <td>${s.elective_type.replace("_", " ")}</td>
                <td>${s.semester}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-secondary" onclick="triggerDownload(${index}, 'pyq')">Download PYQs</button>
                        <button class="btn btn-secondary" onclick="showSyllabusPreview(${index})">Syllabus</button>
                        <button class="btn btn-primary" onclick="triggerDownload(${index}, 'both')">Both</button>
                        <button class="btn btn-secondary" style="border-color: hsl(250, 90%, 65%); color: hsl(250, 90%, 80%);" onclick="triggerAIAnalysis(${index})">🤖 AI Analysis</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);

            // Details Expansion Row
            const detailsTr = document.createElement("tr");
            detailsTr.id = `details-${index}`;
            detailsTr.className = "details-row hidden";
            detailsTr.innerHTML = `
                <td colspan="8">
                    <div class="details-expanded-container">
                        <div class="details-tables-row">
                            <!-- Teaching Scheme Table -->
                            <div class="scheme-table-container">
                                <h4>Teaching Scheme (Hours)</h4>
                                <table class="nested-details-table">
                                    <thead>
                                        <tr>
                                            <th>L</th>
                                            <th>T</th>
                                            <th>P</th>
                                            <th>PBL</th>
                                            <th>Credits</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>${s.lectures || '0'}</td>
                                            <td>${s.tutorial || '0'}</td>
                                            <td>${s.practical || '0'}</td>
                                            <td>${s.pbl || 'NA'}</td>
                                            <td><strong>${s.credits || '0'}</strong></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>

                            <!-- Examination Scheme Table -->
                            <div class="scheme-table-container">
                                <h4>Examination Marks</h4>
                                <table class="nested-details-table">
                                    <thead>
                                        <tr>
                                            <th>Theory (E)</th>
                                            <th>Mid-Sem (M)</th>
                                            <th>Internal (I)</th>
                                            <th>Viva (V)</th>
                                            <th>Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>${s.exam_e || '0'}</td>
                                            <td>${s.exam_m || '0'}</td>
                                            <td>${s.exam_i || '0'}</td>
                                            <td>${s.exam_v || '0'}</td>
                                            <td><strong>${s.exam_total || '0'}</strong></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Details Grid -->
                        <div class="details-params-grid">
                            <div class="param-item"><strong>Category:</strong> <span>${s.detail_category || s.elective_type || 'N/A'}</span></div>
                            <div class="param-item"><strong>Elective Subject:</strong> <span>${s.detail_elective || 'No'}</span></div>
                            <div class="param-item"><strong>Is Theory:</strong> <span>${s.detail_is_theory || 'No'} ${s.detail_theory_duration ? `(Duration: ${s.detail_theory_duration} hrs)` : ''}</span></div>
                            <div class="param-item"><strong>Is Practical:</strong> <span>${s.detail_is_practical || 'No'} ${s.detail_practical_duration ? `(Duration: ${s.detail_practical_duration} hrs)` : ''}</span></div>
                            <div class="param-item"><strong>Is Semipractical:</strong> <span>${s.detail_is_semipractical || 'No'}</span></div>
                            <div class="param-item"><strong>Is Functional:</strong> <span>${s.detail_is_functional || 'No'}</span></div>
                            <div class="param-item"><strong>Remark:</strong> <span>${s.detail_remark || 'N/A'}</span></div>
                        </div>
                    </div>
                </td>
            `;
            tbody.appendChild(detailsTr);
        });
    }

    resultsCard.classList.remove("hidden");
    resultsCard.scrollIntoView({ behavior: "smooth" });
}

function toggleDetails(btn, index) {
    const row = document.getElementById(`details-${index}`);
    const isHidden = row.classList.toggle("hidden");
    
    if (btn) {
        btn.innerText = isHidden ? "▶" : "▼";
        if (isHidden) {
            btn.classList.remove("expanded");
        } else {
            btn.classList.add("expanded");
        }
    }
}

function toggleDetailsFromRow(event, rowEl, index) {
    // If the click was on an action button, checkbox, syllabus link, or similar, ignore
    if (event.target.tagName === 'BUTTON' || event.target.tagName === 'A' || event.target.closest('.action-buttons')) {
        return;
    }
    const btn = rowEl.querySelector(".expand-btn");
    toggleDetails(btn, index);
}

// ── Quick Search ──

// ── Conversational AI Parser Helpers ──

/**
 * Returns true if the query looks like a subject code search
 * (contains a 5+ digit numeric code like 3170719).
 * In that case, the AI parser should NOT fire.
 */
function queryHasSubjectCode(query) {
    return /\b\d{5,}\b/.test(query);
}

function parseConversationalQuery(query) {
    const q = query.toLowerCase().trim();

    // If query contains a 5+ digit subject code, do NOT try to parse as
    // a conversational selector query — let it fall through to code search.
    if (queryHasSubjectCode(query)) {
        return { courseCode: "", branchCode: "", semester: "", academicYear: "" };
    }
    
    // 1. Detect Course
    let courseCode = "";
    if (q.includes("applied science") || q.includes("science")) {
        if (/\bib\b/.test(q)) courseCode = "IB";
        else if (/\bcs\b/.test(q)) courseCode = "CS";
        else if (/\bdb\b/.test(q)) courseCode = "DB";
        else if (/\bim\b/.test(q)) courseCode = "IM";
    } else if (q.includes("part time") || /\bep\b/.test(q)) {
        courseCode = "EP";
    } else if (/\bme\b/.test(q) || q.includes("master of engineering") || q.includes("master")) {
        courseCode = "ME";
    } else if (/\bbe\b/.test(q) || q.includes("bachelor of engineering") || q.includes("bachelor") || q.includes("engineering")) {
        courseCode = "BE";
    }
    
    // 2. Detect Semester — only from explicit "sem X" or "X sem" patterns
    // (avoid picking up random digits from subject names)
    let semester = "";
    const semMatch = q.match(/(?:sem(?:ester)?[- ]?([1-8])\b)|(?:\b([1-8])(?:th|st|nd|rd)?[- ]?sem(?:ester)?\b)|(?:\bs([1-8])\b)/);
    if (semMatch) {
        semester = semMatch[1] || semMatch[2] || semMatch[3];
    }
    // Only fall back to a bare digit if a courseCode was also found
    // (e.g. "BE Computer 7" → semester 7), avoiding false positives on names like "Distributed Systems"
    if (!semester && courseCode) {
        const digitMatch = q.match(/\b([1-8])\b/);
        if (digitMatch) {
            semester = digitMatch[1];
        }
    }
    
    // 3. Detect Branch — only from explicit "branch XX" prefix or
    //    from well-known branch keywords. Do NOT pick random 2-digit runs
    //    from subject names or codes.
    let branchCode = "";
    const explicitBranchMatch = q.match(/branch[- ]?(\d{2})\b/);
    if (explicitBranchMatch) {
        branchCode = explicitBranchMatch[1];
    } else {
        if (q.includes("computer") || /\bce\b/.test(q) || /\bcse\b/.test(q)) {
            branchCode = "07";
        } else if (q.includes("mechanical") || /\bme\b/.test(q)) {
            branchCode = "19";
        } else if (q.includes("civil") || /\bcl\b/.test(q)) {
            branchCode = "06";
        } else if (q.includes("electrical") || /\bee\b/.test(q)) {
            branchCode = "09";
        } else if (q.includes("information technology") || /\bit\b/.test(q)) {
            branchCode = "16";
        } else if (q.includes("electronics") || /\bec\b/.test(q)) {
            branchCode = "11";
        }
    }
    
    // 4. Academic Year
    let academicYear = "";
    const yearMatch = q.match(/\b(20\d{2}-\d{2})\b/);
    if (yearMatch) {
        academicYear = yearMatch[1];
    }
    
    return { courseCode, branchCode, semester, academicYear };
}

async function autofillSelectorCascade(course, branch, sem, year) {
    appendConsoleLog(`[AI PARSER] Resolving query: Course=${course || '?'}, Branch=${branch || '?'}, Sem=${sem || '?'}, Year=${year || '?'}`, "system");
    
    const courseSelect = document.getElementById("course-select");
    const branchSelect = document.getElementById("branch-select");
    const semSelect = document.getElementById("sem-select");
    const yearSelect = document.getElementById("year-select");
    const electiveSelect = document.getElementById("elective-select");
    
    if (course) {
        courseSelect.value = course;
        await handleCourseChange.call(courseSelect);
    }
    if (branch) {
        const option = branchSelect.querySelector(`option[value="${branch}"]`);
        if (option) {
            branchSelect.value = branch;
        } else {
            const lowerBranch = branch.toLowerCase();
            let matched = false;
            for (let i = 0; i < branchSelect.options.length; i++) {
                const opt = branchSelect.options[i];
                if (opt.text.toLowerCase().includes(lowerBranch)) {
                    branchSelect.value = opt.value;
                    matched = true;
                    break;
                }
            }
            if (!matched && branchSelect.options.length > 1) {
                branchSelect.selectedIndex = 1;
            }
        }
        await handleBranchChange.call(branchSelect);
    }
    if (sem) {
        semSelect.value = sem;
        await handleSemesterChange.call(semSelect);
    }
    
    if (year) {
        if (yearSelect.querySelector(`option[value="${year}"]`)) {
            yearSelect.value = year;
        } else if (yearSelect.options.length > 1) {
            yearSelect.selectedIndex = 1;
        }
    } else {
        if (yearSelect.options.length > 1 && !yearSelect.value) {
            yearSelect.selectedIndex = 1;
        }
    }
    
    if (electiveSelect.options.length > 0 && !electiveSelect.value) {
        electiveSelect.selectedIndex = 0; // All
    }
    appendConsoleLog(`[AI PARSER] Portal selectors populated.`, "success");
}

// ── Quick Search ──

function handleQuickSearchInput() {
    clearTimeout(quickSearchDebounceTimer);
    const query = document.getElementById("quick-search").value.trim();
    const dropdown = document.getElementById("quick-search-results");

    if (!query) {
        dropdown.classList.add("hidden");
        return;
    }

    quickSearchDebounceTimer = setTimeout(async () => {
        appendConsoleLog(`[SEARCH] Querying cache for: "${query}"...`, "info");
        const results = await apiGet(`/api/search?q=${encodeURIComponent(query)}`);
        dropdown.innerHTML = "";

        // Add special Conversational AI auto-fill action if parsed parameters are found
        const parsed = parseConversationalQuery(query);
        if (parsed.courseCode || parsed.branchCode || parsed.semester) {
            const aiItem = document.createElement("div");
            aiItem.className = "quick-item";
            aiItem.style.background = "rgba(99, 102, 241, 0.08)";
            aiItem.style.borderLeft = "3px solid var(--cyan-accent)";
            
            let label = "✨ AI Action: Configure portal search for ";
            let parts = [];
            if (parsed.courseCode) parts.push(`Course [${parsed.courseCode}]`);
            if (parsed.branchCode) parts.push(`Branch [${parsed.branchCode}]`);
            if (parsed.semester) parts.push(`Sem [${parsed.semester}]`);
            if (parsed.academicYear) parts.push(`Year [${parsed.academicYear}]`);
            label += parts.join(", ");
            
            aiItem.innerHTML = `<strong>${label}</strong> <span style="font-size: 11px; color: var(--cyan-accent); margin-left: 10px;">(Click to populate selectors)</span>`;
            aiItem.addEventListener("click", async () => {
                dropdown.classList.add("hidden");
                document.getElementById("quick-search").value = "";
                showToast("AI Auto-configuring selectors...", "success");
                await autofillSelectorCascade(parsed.courseCode, parsed.branchCode, parsed.semester, parsed.academicYear);
                showToast("Scraping subjects...", "success");
                searchSubjects();
            });
            dropdown.appendChild(aiItem);
        }

        if (results && results.length > 0) {
            results.forEach(s => {
                const item = document.createElement("div");
                item.className = "quick-item";
                item.innerHTML = `<span class="code-span">${s.subject_code}</span> <strong>${s.subject_name}</strong> <span style="font-size: 11px; color: var(--text-secondary); margin-left: 10px;">(Sem ${s.semester}, ${s.course})</span>`;
                item.addEventListener("click", () => {
                    dropdown.classList.add("hidden");
                    appendConsoleLog(`[SEARCH] Selected ${s.subject_name} (${s.subject_code})`, "success");
                    displayResults([s], `Fuzzy Search Match: [${s.subject_code}]`);
                });
                dropdown.appendChild(item);
            });
            dropdown.classList.remove("hidden");
        } else {
            if (dropdown.children.length === 0) {
                dropdown.innerHTML = `<div style="padding: 12px 20px; color: var(--text-muted); font-size: 13.5px;">No matches found in cache. Try selecting dropdown options to fetch live data.</div>`;
            }
            dropdown.classList.remove("hidden");
        }
    }, 300);
}

async function performQuickSearch() {
    const input = document.getElementById("quick-search");
    const query = input.value.trim();
    const dropdown = document.getElementById("quick-search-results");
    
    if (!query) return;
    
    dropdown.classList.add("hidden");
    
    // Check if query is conversational AI pattern (only if NO subject code present)
    const parsed = parseConversationalQuery(query);
    if (parsed.courseCode || parsed.branchCode || parsed.semester) {
        showToast("AI parsed query. Auto-configuring selectors...", "success");
        input.value = "";
        await autofillSelectorCascade(parsed.courseCode, parsed.branchCode, parsed.semester, parsed.academicYear);
        searchSubjects();
        return;
    }
    
    // Direct subject/name search — show live-search loading toast
    showToast("🔍 Searching live GTU portal...", "success");
    appendConsoleLog(`[SEARCH] Fetching live results for: "${query}"...`, "info");
    
    const results = await apiGet(`/api/search?q=${encodeURIComponent(query)}`);
    if (results && results.length > 0) {
        appendConsoleLog(`[SEARCH] Search returned ${results.length} result(s).`, "success");
        displayResults(results, `Live Search Results for "${query}"`);
        showToast(`✅ Found ${results.length} matching subject(s).`, "success");
    } else {
        appendConsoleLog(`[SEARCH] No subjects found for "${query}".`, "error");
        showToast(`❌ No subjects found for "${query}". Check spelling or try with subject code.`, "error");
    }
}

function handleDocumentClick(event) {
    const searchSection = document.querySelector(".quick-search-section");
    const dropdown = document.getElementById("quick-search-results");
    if (!searchSection.contains(event.target)) {
        dropdown.classList.add("hidden");
    }
}

// ── Downloads Logic & Modal progress ──

async function triggerDownload(index, type) {
    const s = currentSubjectsList[index];
    if (!s) return;

    activeSubjectIndex = index;
    activeDownloadType = type;

    appendConsoleLog(`[DOWNLOAD] Opening configuration panel for [${s.subject_code}] - type: ${type}`, "info");

    // Show modal
    const modal = document.getElementById("download-modal");
    document.getElementById("modal-sub-code").innerText = s.subject_code;
    document.getElementById("modal-sub-name").innerText = s.subject_name;
    document.getElementById("modal-footer").classList.add("hidden");

    // Show config section and hide progress section initially
    document.getElementById("modal-title").innerText = "Configure Download Settings";
    document.getElementById("modal-config-section").classList.remove("hidden");
    document.getElementById("modal-progress-section").classList.add("hidden");

    // Fetch current settings from backend to populate options
    const settings = await apiGet("/api/settings");
    if (settings) {
        document.getElementById("modal-merge-order").value = settings.default_merge_order || "ascending";
        document.getElementById("modal-session-order").value = settings.default_session_order || "winter-first";
    }

    modal.classList.remove("hidden");
}

async function startActualDownload() {
    if (activeSubjectIndex === null || activeDownloadType === null) return;
    const s = currentSubjectsList[activeSubjectIndex];
    const type = activeDownloadType;

    // Read custom settings values from inputs
    const startYear = document.getElementById("modal-start-year").value;
    const endYear = document.getElementById("modal-end-year").value;
    const mergeOrder = document.getElementById("modal-merge-order").value;
    const sessionOrder = document.getElementById("modal-session-order").value;

    appendConsoleLog(`[DOWNLOAD] Initializing download pipeline for subject [${s.subject_code}]`, "system");

    // Transition UI to progress view
    document.getElementById("modal-title").innerText = "Processing Resource Download";
    document.getElementById("modal-config-section").classList.add("hidden");
    document.getElementById("modal-progress-section").classList.remove("hidden");

    // Reset steps
    const stepInit = document.getElementById("step-init");
    const stepPyq = document.getElementById("step-pyq");
    const stepSyllabus = document.getElementById("step-syllabus");
    const stepComplete = document.getElementById("step-complete");

    setStep(stepInit, "active");
    setStep(stepPyq, "pending");
    setStep(stepSyllabus, "pending");
    setStep(stepComplete, "pending");

    setProgress(5);

    // Phase 1: Init directories
    await wait(800);
    setStep(stepInit, "done");
    appendConsoleLog(`[INIT] Directories initialized successfully.`, "success");
    
    // Set active next phase
    if (type === "pyq" || type === "both") {
        setStep(stepPyq, "active");
        setProgress(30);
        appendConsoleLog(`[PYQ] Scraping PYQ sessions from ${startYear} to ${endYear} (${sessionOrder}, sorting ${mergeOrder})...`, "info");
    } else {
        setStep(stepPyq, "pending");
    }
    
    if (type === "syllabus" || type === "both") {
        if (type !== "both") {
            setStep(stepSyllabus, "active");
            setProgress(35);
        }
        appendConsoleLog(`[SYLLABUS] Crawling syllabus from GTU servers (effective since ${s.academic_year || 'June 2021'})...`, "info");
    }

    // Call server API for actual download execution with custom settings overrides
    const result = await apiPost("/api/download", {
        subject: s,
        type: type,
        settings: {
            start_year: parseInt(startYear),
            end_year: parseInt(endYear),
            merge_order: mergeOrder,
            session_order: sessionOrder
        }
    });

    if (result && result.status === "success") {
        const res = result.results;
        
        if (type === "pyq" || type === "both") {
            if (res.pyq_success) {
                setStep(stepPyq, "done");
                setProgress(70);
                appendConsoleLog(`[PYQ] Downloaded ${res.pyq_found} sessions. Merged target PDF successfully.`, "success");
                if (res.pyq_url) {
                    downloadFile(res.pyq_url, `PYQ_${s.subject_code}.pdf`);
                }
            } else {
                setStep(stepPyq, "error");
                appendConsoleLog(`[PYQ] Scrape/Merge failed: ${res.pyq_error || "No papers found"}`, "error");
                showToast(`PYQ Download failed: ${res.pyq_error || "Unknown error"}`, "error");
            }
        }
        
        if (type === "syllabus" || type === "both") {
            if (type === "both") {
                setStep(stepSyllabus, "active");
                await wait(400);
            }
            if (res.syllabus_success) {
                setStep(stepSyllabus, "done");
                setProgress(90);
                appendConsoleLog(`[SYLLABUS] Syllabus PDF scraped successfully.`, "success");
                if (res.syllabus_url) {
                    downloadFile(res.syllabus_url, `Syllabus_${s.subject_code}.pdf`);
                }
            } else {
                setStep(stepSyllabus, "error");
                appendConsoleLog(`[SYLLABUS] Scrape failed: ${res.syllabus_error || "Timeout"}`, "error");
                showToast(`Syllabus Download failed: ${res.syllabus_error || "Unknown error"}`, "error");
            }
        }

        setStep(stepComplete, "active");
        await wait(400);
        setStep(stepComplete, "done");
        setProgress(100);

        const linksDiv = document.getElementById("modal-download-links");
        if (linksDiv) {
            linksDiv.innerHTML = "";
            linksDiv.classList.remove("hidden");

            if (res.pyq_url) {
                const pyqBtn = document.createElement("a");
                pyqBtn.href = res.pyq_url;
                pyqBtn.target = "_blank";
                pyqBtn.rel = "noopener noreferrer";
                pyqBtn.className = "btn btn-primary";
                pyqBtn.style.cssText = "display: flex; align-items: center; justify-content: center; gap: 8px; font-weight: 600; text-decoration: none; padding: 12px; font-size: 14px; width: 100%; box-sizing: border-box; margin-bottom: 10px;";
                pyqBtn.innerHTML = `📄 Open / View Merged PYQ PDF`;
                linksDiv.appendChild(pyqBtn);

                // Auto open in new tab
                window.open(res.pyq_url, "_blank");
            }

            if (res.syllabus_url) {
                const sylBtn = document.createElement("a");
                sylBtn.href = res.syllabus_url;
                sylBtn.target = "_blank";
                sylBtn.rel = "noopener noreferrer";
                sylBtn.className = "btn btn-secondary";
                sylBtn.style.cssText = "display: flex; align-items: center; justify-content: center; gap: 8px; font-weight: 600; text-decoration: none; padding: 12px; font-size: 14px; width: 100%; box-sizing: border-box;";
                sylBtn.innerHTML = `📖 Open / View Syllabus PDF`;
                linksDiv.appendChild(sylBtn);
            }
        }

        appendConsoleLog(`[DOWNLOAD] All tasks completed successfully.`, "success");
        showToast("Resources downloaded and ready!", "success");
    } else {
        setStep(stepPyq, "error");
        setStep(stepSyllabus, "error");
        setStep(stepComplete, "error");
        appendConsoleLog(`[DOWNLOAD] Critical pipeline execution exception in backend server.`, "error");
        showToast("Critical backend error on download request", "error");
    }

    // Show Close button
    document.getElementById("modal-footer").classList.remove("hidden");
}

function showSyllabusPreview(index) {
    const s = currentSubjectsList[index];
    if (!s || !s.syllabus_pdf_url) {
        showToast("No syllabus PDF URL available for this subject", "error");
        return;
    }
    window.open(s.syllabus_pdf_url, "_blank");
}

function closeSyllabusModal() {
    const modal = document.getElementById("syllabus-modal");
    modal.classList.add("hidden");
    document.getElementById("syllabus-iframe").src = "";
}

async function downloadSyllabusDirect(index) {
    const s = currentSubjectsList[index];
    if (!s) return;

    showToast("Downloading syllabus...", "success");
    const result = await apiPost("/api/download", { subject: s, type: "syllabus" });
    if (result && result.status === "success" && result.results.syllabus_url) {
        downloadFile(result.results.syllabus_url, `Syllabus_${s.subject_code}.pdf`);
        showToast("Syllabus downloaded successfully!", "success");
    } else {
        showToast("Syllabus download failed.", "error");
    }
}

function downloadFile(url, fileName) {
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function setStep(el, state) {
    el.className = `step ${state}`;
}

function setProgress(val) {
    document.getElementById("progress-bar-fill").style.width = `${val}%`;
}

function closeModal() {
    document.getElementById("download-modal").classList.add("hidden");
}

function showToast(message, type = "success") {
    const t = document.getElementById("toast");
    t.innerText = message;
    t.className = `toast visible ${type}`;
    t.classList.remove("hidden");
    
    setTimeout(() => {
        t.classList.remove("visible");
        setTimeout(() => t.classList.add("hidden"), 300);
    }, 4000);
}

async function loadSettings() {
    // Optional: Left as stub since settings panel is removed
}

async function saveSettings() {
    // Optional: Left as stub since settings panel is removed
}

// ── Footer Policy Modals (Option B) ──

const INFO_DETAILS = {
    dmca: {
        title: "DMCA Policy",
        content: `
            <p><strong>GTU Academic Engine V2</strong> is a community-driven, open-source educational utility developed for engineering students. All syllabi, teaching schemes, examination structures, and previous year question papers (PYQs) are fetched directly on-demand or cached index-wise from the official public portal of <strong>Gujarat Technological University (GTU)</strong>.</p>
            <br>
            <p>We do not host or claim ownership of any official academic materials, PDFs, or university publications. All trademarks, logos, copyrights, and intellectual property remain the sole property of Gujarat Technological University.</p>
            <br>
            <p>If you represent GTU or are a copyright holder wishing to request the removal of specific indexed materials or search references from this engine, please contact the developer via email at <a href="mailto:nishitsavaliya.me@gmail.com" style="color: hsl(250, 90%, 75%); text-decoration: underline;">nishitsavaliya.me@gmail.com</a>. We will process your request and remove the reference paths within 48 hours.</p>
        `
    },
    disclaimer: {
        title: "Disclaimer",
        content: `
            <p>This application is <strong>unofficial</strong> and is not affiliated, associated, authorized, endorsed by, or in any way officially connected with <strong>Gujarat Technological University (GTU)</strong> or any of its departments.</p>
            <br>
            <p>The information provided in this web interface (such as syllabus credits, hours, and exams schemes) is gathered from scraped data and is cached locally to improve retrieval times. Although we make every effort to keep the information accurate and up-to-date, the official GTU portal (<a href="https://www.gtu.ac.in/" target="_blank" rel="noopener noreferrer" style="color: hsl(250, 90%, 75%); text-decoration: underline;">gtu.ac.in</a>) remains the absolute source of truth.</p>
            <br>
            <p>The developer, <strong>Nishit Savaliya</strong>, makes no warranties or representations of any kind concerning the reliability, completeness, suitability, or availability of the scraped content. Any reliance you place on such information is strictly at your own risk.</p>
        `
    },
    privacy: {
        title: "Privacy Policy",
        content: `
            <p>We respect your privacy and design our applications to store resources locally. <strong>GTU Academic Engine V2</strong> operates under the following guidelines:</p>
            <br>
            <ul style="padding-left: 20px; list-style-type: disc;">
                <li style="margin-bottom: 10px;"><strong>Local Storage:</strong> All download histories, custom configurations, settings, and scraped subject records are stored on your local host storage (e.g. <code>history.json</code>, <code>settings.json</code>, and local downloads folders).</li>
                <li style="margin-bottom: 10px;"><strong>No Tracking:</strong> This website does not use tracking cookies, analytics scripts, or external telemetry software. No personal data is sent to the developer.</li>
                <li style="margin-bottom: 10px;"><strong>Third-Party Requests:</strong> When searching or downloading syllabus files and question papers, requests are sent directly to official GTU server ports to fetch live documents. Those requests are subject to GTU's own network policies.</li>
            </ul>
        `
    },
    terms: {
        title: "Terms & Conditions",
        content: `
            <p>By using the <strong>GTU Academic Engine V2</strong>, you agree to comply with the following conditions:</p>
            <br>
            <ul style="padding-left: 20px; list-style-type: disc;">
                <li style="margin-bottom: 10px;"><strong>Educational Use Only:</strong> The software is provided solely for educational, syllabus reference, and personal preparation purposes. Commercial resale or redistribution of merged documents is prohibited.</li>
                <li style="margin-bottom: 10px;"><strong>Responsible Crawling:</strong> You agree not to launch DDoS attacks, spam requests, or manipulate search endpoints to flood the GTU portal. The engine implements strict caching to prevent unnecessary load on university systems.</li>
                <li style="margin-bottom: 10px;"><strong>MIT License:</strong> The source code of this tool is provided "as is" under the MIT License. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability.</li>
            </ul>
        `
    },
    about: {
        title: "About Us",
        content: `
            <p><strong>GTU Academic Engine V2</strong> is a state-of-the-art developer utility created to solve the fragmentation of syllabus portals and examination resources for engineering branches under GTU.</p>
            <br>
            <p>Key Features:</p>
            <ul style="padding-left: 20px; list-style-type: disc; margin: 10px 0;">
                <li style="margin-bottom: 5px;">Automated syllabus crawling across multiple courses & branch structures.</li>
                <li style="margin-bottom: 5px;">Centralized cache management for near-instant subject searches.</li>
                <li style="margin-bottom: 5px;">On-demand, customizable Previous Year Question (PYQ) download pipelines with PDF merging options.</li>
            </ul>
            <br>
            <p>This project is open-source and maintained on GitHub at <a href="https://github.com/Nishit3116/GTU" target="_blank" rel="noopener noreferrer" style="color: hsl(250, 90%, 75%); text-decoration: underline;">github.com/Nishit3116/GTU</a>. Contributions, bug reports, and features suggestions are welcome!</p>
        `
    },
    contact: {
        title: "Contact Us",
        content: `
            <p>If you have any questions, feedback, or need assistance, you can reach out directly:</p>
            <br>
            <div style="background: hsla(224, 25%, 12%, 0.5); padding: 15px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
                <p><strong>Developer:</strong> Nishit Savaliya</p>
                <p><strong>Email:</strong> <a href="mailto:nishitsavaliya.me@gmail.com" style="color: hsl(250, 90%, 75%); text-decoration: underline;">nishitsavaliya.me@gmail.com</a></p>
                <p><strong>GitHub Profile:</strong> <a href="https://github.com/Nishit3116" target="_blank" rel="noopener noreferrer" style="color: hsl(250, 90%, 75%); text-decoration: underline;">github.com/Nishit3116</a></p>
                <p><strong>Project Codebase:</strong> <a href="https://github.com/Nishit3116/GTU" target="_blank" rel="noopener noreferrer" style="color: hsl(250, 90%, 75%); text-decoration: underline;">github.com/Nishit3116/GTU</a></p>
            </div>
            <br>
            <p>We welcome pull requests and suggestions on GitHub to improve caching mechanisms, expand branch coverages, and optimize the scraping handlers.</p>
        `
    }
};

function openInfoModal(topic) {
    const data = INFO_DETAILS[topic];
    if (!data) return;

    document.getElementById("info-modal-title").innerText = data.title;
    document.getElementById("info-modal-body").innerHTML = data.content;
    document.getElementById("info-modal").classList.remove("hidden");
}

function closeInfoModal() {
    document.getElementById("info-modal").classList.add("hidden");
}

function handleInfoOverlayClick(event) {
    if (event.target.id === "info-modal") {
        closeInfoModal();
    }
}

async function triggerAIAnalysis(index) {
    const s = currentSubjectsList[index];
    if (!s) return;

    const modal = document.getElementById("ai-analysis-modal");
    document.getElementById("ai-modal-title").innerText = `🤖 AI Analysis: ${s.subject_code} - ${s.subject_name}`;
    document.getElementById("ai-modal-subtitle").innerText = `5-Dimensional Intelligence Breakdown | GTU Academic Engine V2`;

    const modalBody = document.getElementById("ai-modal-body");
    modalBody.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="spinner" style="display: inline-block; width: 32px; height: 32px; border: 3px solid rgba(255,255,255,0.1); border-top-color: hsl(250, 90%, 75%); border-radius: 50%; animation: spin 1s infinite linear;"></div>
            <p style="margin-top: 15px; color: var(--text-secondary);">Analyzing question paper patterns, weightages, and generating predictions...</p>
        </div>
    `;
    modal.classList.remove("hidden");

    try {
        const queryUrl = `/api/analyze?subject_code=${s.subject_code}&subject_name=${encodeURIComponent(s.subject_name)}&course=${s.course}&branch=${s.branch}&sem=${s.semester}`;
        const res = await apiGet(queryUrl);

        if (!res || res.status === "error") {
            modalBody.innerHTML = `<div style="color: var(--danger-color); padding: 20px; text-align: center;">Failed to analyze subject papers.</div>`;
            return;
        }

        renderAIAnalysisResult(res, s);
    } catch (err) {
        modalBody.innerHTML = `<div style="color: var(--danger-color); padding: 20px; text-align: center;">Analysis error: ${err.message}</div>`;
    }
}

function renderAIAnalysisResult(res, s) {
    const modalBody = document.getElementById("ai-modal-body");
    
    // Marks Breakdown Badges
    const mb = res.marks_breakdown || {};
    const marksHtml = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 25px;">
            <div style="background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.3); padding: 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 11px; color: #a5b4fc; text-transform: uppercase; font-weight: 600;">3-Mark Questions</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin-top: 4px;">${mb["3_marks_count"] || 0} <span style="font-size: 12px; color: var(--text-secondary);">(${mb["3_marks_pct"] || 0}%)</span></div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); padding: 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 11px; color: #6ee7b7; text-transform: uppercase; font-weight: 600;">4-Mark Questions</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin-top: 4px;">${mb["4_marks_count"] || 0} <span style="font-size: 12px; color: var(--text-secondary);">(${mb["4_marks_pct"] || 0}%)</span></div>
            </div>
            <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); padding: 12px; border-radius: 8px; text-align: center;">
                <div style="font-size: 11px; color: #fcd34d; text-transform: uppercase; font-weight: 600;">7-Mark Questions</div>
                <div style="font-size: 22px; font-weight: 700; color: #fff; margin-top: 4px;">${mb["7_marks_count"] || 0} <span style="font-size: 12px; color: var(--text-secondary);">(${mb["7_marks_pct"] || 0}%)</span></div>
            </div>
        </div>
    `;

    // Chapter Breakdown & Weightage Progress Bars
    const chapters = res.chapter_breakdown || [];
    let chapterHtml = `<h4 style="margin: 0 0 12px 0; color: var(--text-primary); font-size: 15px;">📚 Chapter-wise Marks & Weightage Breakdown</h4>`;
    chapterHtml += `<div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 25px;">`;
    chapters.forEach(c => {
        chapterHtml += `
            <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; border: 1px solid var(--border-color);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13.5px;">
                    <span style="font-weight: 600; color: hsl(250, 90%, 80%);">${c.chapter_name}</span>
                    <span style="color: var(--text-secondary); font-weight: 600;">${c.weightage_percentage}% Weightage (${c.total_marks} Marks)</span>
                </div>
                <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden;">
                    <div style="width: ${c.weightage_percentage}%; height: 100%; background: linear-gradient(90deg, #6366f1, #a855f7);"></div>
                </div>
            </div>
        `;
    });
    chapterHtml += `</div>`;

    // AI Predicted Questions
    const predicted = res.predicted_questions || [];
    let predHtml = `<h4 style="margin: 0 0 12px 0; color: var(--text-primary); font-size: 15px;">🔮 AI Predicted High-Probability Questions for Upcoming Exam</h4>`;
    predHtml += `<div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 25px;">`;
    predicted.forEach((p, pIdx) => {
        const isHigh = p.probability.includes("HIGH");
        const badgeBg = isHigh ? "rgba(239, 68, 68, 0.2)" : "rgba(245, 158, 11, 0.2)";
        const badgeBorder = isHigh ? "#ef4444" : "#f59e0b";
        const badgeColor = isHigh ? "#fca5a5" : "#fcd34d";

        predHtml += `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-left: 4px solid ${badgeBorder}; padding: 14px; border-radius: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 12px; font-weight: 600; color: var(--text-muted);">${p.chapter} | ${p.marks} Marks</span>
                    <span style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeBorder}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px;">${p.probability} LIKELIHOOD</span>
                </div>
                <div style="font-size: 14px; color: #fff; font-weight: 500; line-height: 1.4;">${pIdx + 1}. ${p.question_text}</div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 6px; font-style: italic;">Reason: ${p.reason}</div>
            </div>
        `;
    });
    predHtml += `</div>`;

    modalBody.innerHTML = marksHtml + chapterHtml + predHtml;
}

function closeAIModal() {
    document.getElementById("ai-analysis-modal").classList.add("hidden");
}

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));
