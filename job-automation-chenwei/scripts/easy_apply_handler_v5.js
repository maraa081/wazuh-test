// JavaScript handler for LinkedIn Easy Apply modal (passed to page.evaluate)
function easyApplyHandler(step, hasFileDetectedAlready, answers) {
    // STEP A: Fill all form fields AND detect file inputs
    const allFields = document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea, select, input[type=file]');
    let lastWasCountry = false;
    let filled = [];
    let hasFileInput = false;
    
    for (const field of allFields) {
        if (field.type === 'file') {
            hasFileInput = true;
            filled.push({field: 'FILE-input:' + field.id, type: 'file', value: 'NEED_UPLOAD'});
            continue;
        }
        if (field.value && field.value.trim()) {
            lastWasCountry = field.value.includes('+33');
            continue;
        }
        const tag = field.tagName.toLowerCase();
        const type = (field.getAttribute('type') || '').toLowerCase();
        const ph = (field.getAttribute('placeholder') || '').toLowerCase();
        const aria = (field.getAttribute('aria-label') || '').toLowerCase();
        const name = (field.getAttribute('name') || '').toLowerCase();
        const cl = (field.className || '').toLowerCase();
        const combined = ph + ' ' + aria + ' ' + name + ' ' + type + ' ' + cl;
        
        if (combined.includes('chercher') || combined.includes('search') || combined.includes('recherch')) {
            lastWasCountry = false; continue;
        }
        if (field.value && field.value.trim()) continue;
        
        let answer = null;
        if (lastWasCountry || type === 'tel' || name.includes('phone') || name.includes('mobile')) {
            answer = answers.phone;
        } else if (combined.includes('telephone') || combined.includes('phone') || combined.includes('mobile') || combined.includes('portable') || combined.includes('numero') || combined.includes('fixe') || combined.includes('+33') || combined.includes('06') || combined.includes('07')) {
            answer = answers.phone;
        } else if (combined.includes('portfolio') || combined.includes('site') || combined.includes('lien web') || combined.includes('url')) {
            answer = answers.portfolio;
        } else if (combined.includes('linkedin')) {
            answer = answers.linkedin;
        } else if (combined.includes('email') || combined.includes('courriel') || combined.includes('mail') || combined.includes('e-mail')) {
            answer = answers.email;
        } else if (combined.includes('motivation') || combined.includes('lettre') || combined.includes('pourquoi')) {
            answer = answers.motivation;
        } else if (combined.includes('salaire') || combined.includes('pretention') || combined.includes('remuneration')) {
            answer = answers.salary;
        } else if (combined.includes('disponible') || combined.includes('commencer') || combined.includes('debut')) {
            answer = answers.availability;
        } else if (combined.includes('experience') || combined.includes('parcours') || combined.includes('formation')) {
            answer = answers.experience;
        } else if (combined.includes('logiciel') || combined.includes('adobe') || combined.includes('competence') || combined.includes('outil')) {
            answer = answers.skills;
        } else if ((combined.includes('langue') || combined.includes('langage')) && !combined.includes('programmation')) {
            answer = answers.languages;
        } else if (combined.includes('visa') || combined.includes('sponsor') || combined.includes('travail') || combined.includes('autorisation')) {
            answer = answers.visa;
        } else if (combined.includes('rythme') || combined.includes('alternance') || combined.includes('temps')) {
            answer = answers.rhythm;
        } else if (combined.includes('annee') || combined.includes('years') || combined.includes('duree')) {
            answer = answers.years;
        } else if (combined.includes('souhaitez') || combined.includes('poste') || combined.includes('role') || combined.includes('titre') || combined.includes('fonction') || combined.includes('intitule') || combined.includes('position')) {
            answer = answers.role;
        } else if (tag === 'input' && type === 'text' && !ph && !aria && !name) {
            answer = answers.phone;
        }
        
        if (answer) {
            field.focus();
            field.value = '';
            field.value = answer;
            field.dispatchEvent(new Event('input', {bubbles: true}));
            field.dispatchEvent(new Event('change', {bubbles: true}));
            filled.push({field: tag + '#' + (field.id || ''), type: type, value: answer.substring(0,15)});
        }
        lastWasCountry = field.value && field.value.includes('+33');
    }
    
    // If file input found and Python hasn't uploaded yet, skip
    if (hasFileInput && !hasFileDetectedAlready) {
        return JSON.stringify({
            filledCount: filled.length, filled: filled.slice(0,3),
            button: null, step: step, done: false, hasFile: true
        });
    }
    
    // STEP B: Find and click next/submit button
    const allBtns = document.querySelectorAll('button');
    const skipNavText = ['vous', 'emplois', 'reseau', 'messagerie', 'notification', 'accueil', 'profil', 'jobs', 'network', 'messaging', 'notifications', 'home', 'raccourci', 'fermer le menu', 'acceder a la recherche', 'passer au contenu', 'conditions', 'solutions', 'telecharger', 'plus', 'publicite', 'toutes les candidatures'];
    let btnClicked = null;
    const nextTerms = ['suivant', 'next', 'continuer', 'continue', 'examiner', 'review', 'envoyer', 'submit', 'postuler', 'apply', 'send', 'done', 'termine', 'terminer'];
    
    for (const btn of allBtns) {
        if (btn.offsetParent === null) continue;
        const t = (btn.textContent || '').trim().toLowerCase();
        if (!t) continue;
        if (skipNavText.some(s => t === s)) continue;
        if (nextTerms.some(term => t === term || t.startsWith(term))) {
            btn.click();
            btnClicked = t.substring(0,20);
            break;
        }
    }
    if (!btnClicked) {
        for (const btn of allBtns) {
            if (btn.offsetParent === null) continue;
            const t = (btn.textContent || '').trim().toLowerCase();
            if (!t) continue;
            if (skipNavText.some(s => t.includes(s))) continue;
            const cl = (btn.className || '').toLowerCase();
            if (cl.includes('primary')) {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 50) { btn.click(); btnClicked = 'pri:' + t.substring(0,15); break; }
            }
        }
    }
    if (!btnClicked) {
        const candidates = Array.from(allBtns).filter(b => {
            if (b.offsetParent === null) return false;
            const t = (b.textContent || '').trim().toLowerCase();
            if (!t) return false;
            const skip = ['fermer', 'close', 'cancel', 'annuler', 'x', '...', 'enregistrer', 'save', 'suivre', 'follow', 'vous', 'emplois', 'accueil', 'messagerie', 'plus', 'partager'];
            return !skip.some(s => t === s || t.startsWith(s));
        });
        candidates.sort((a,b) => {
            const ra = a.getBoundingClientRect();
            const rb = b.getBoundingClientRect();
            return (rb.top + rb.height) - (ra.top + ra.height);
        });
        if (candidates.length > 0) {
            const btn = candidates[0];
            const rect = btn.getBoundingClientRect();
            if (rect.width > 50 && rect.height > 20) {
                btn.click();
                btnClicked = 'pos:' + (btn.textContent || '').trim().substring(0,15);
            }
        }
    }
    
    // Check if done - only by success buttons
    const allBtns2 = document.querySelectorAll('button');
    const hasSubmitAnother = Array.from(allBtns2).some(b => (b.textContent || '').includes('Envoyer une autre candidature'));
    const hasDoneBtn = Array.from(allBtns2).some(b => {
        const t = (b.textContent || '').trim();
        return ['Terminer', 'Termin' + String.fromCharCode(233), 'Termin' + String.fromCharCode(233) + 'e', 'Done', 'Dismiss', 'Fermer'].includes(t);
    });
    const done = hasSubmitAnother || hasDoneBtn;
    
    return JSON.stringify({
        filledCount: filled.length, filled: filled.slice(0,3),
        button: btnClicked, step: step, done: done, hasFile: hasFileInput
    });
}
