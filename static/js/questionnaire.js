// ═══════════════════════════════════════════════════════
//  Questionnaire — Module JS
//  Collecte des réponses, validation, soumission
// ═══════════════════════════════════════════════════════

const Questionnaire = {

    // ─── Init ───────────────────────────────────────────
    init() {
        this.setupCheckboxLimits();
        this.setupProgressTracking();
        this.updateProgress();
    },

    // ─── Limiter les checkboxes QCM à 3 max ─────────────
    setupCheckboxLimits() {
        document.querySelectorAll('input[type="checkbox"][data-max]').forEach(cb => {
            cb.addEventListener('change', function () {
                const max = parseInt(this.dataset.max);
                const name = this.name;
                const checked = document.querySelectorAll(`input[name="${name}"]:checked`);
                if (checked.length > max) {
                    this.checked = false;
                    alert(`Vous ne pouvez sélectionner que ${max} options maximum.`);
                }
                Questionnaire.updateProgress();
            });
        });
    },

    // ─── Suivi de la progression ─────────────────────────
    setupProgressTracking() {
        // Ecouter tous les changements de réponses
        document.querySelectorAll('input[type="radio"]').forEach(el => {
            el.addEventListener('change', () => this.updateProgress());
        });
        document.querySelectorAll('textarea.open-answer').forEach(el => {
            el.addEventListener('input', () => this.updateProgress());
        });
    },

    updateProgress() {
        const totalQuestions = document.querySelectorAll('.question-block:not([style*="display: none"])').length;
        if (totalQuestions === 0) return;

        let answered = 0;

        // Compter les radios répondus (par groupe unique de name)
        const radioGroups = new Set();
        document.querySelectorAll('.question-block:not([style*="display: none"]) input[type="radio"]').forEach(r => {
            radioGroups.add(r.name);
        });
        radioGroups.forEach(name => {
            if (document.querySelector(`input[name="${name}"]:checked`)) {
                answered++;
            }
        });

        // Compter les checkboxes répondues (au moins 1 cochée par groupe)
        const checkGroups = new Set();
        document.querySelectorAll('.question-block:not([style*="display: none"]) input[type="checkbox"]').forEach(c => {
            checkGroups.add(c.name);
        });
        checkGroups.forEach(name => {
            if (document.querySelector(`input[name="${name}"]:checked`)) {
                answered++;
            }
        });

        // Compter les textareas remplies
        document.querySelectorAll('.question-block:not([style*="display: none"]) textarea.open-answer').forEach(ta => {
            if (ta.value.trim().length > 0) {
                answered++;
            }
        });

        const percent = Math.round((answered / totalQuestions) * 100);
        const bar = document.getElementById('progress-bar');
        const text = document.getElementById('progress-text');
        if (bar) bar.style.width = percent + '%';
        if (text) text.textContent = percent + '% complete';
    },

    // ─── Toggle Prof Block (mode INCLUSIF) ──────────────
    toggleProfBlock(radio) {
        const profBlock = radio.closest('.prof-block-optional');
        if (!profBlock) return;

        const conditionalBlock = profBlock.querySelector('.prof-conditional-block');
        if (!conditionalBlock) return;

        // "Oui" = première option
        const isYes = radio.value.toLowerCase().includes('oui') || radio.value.toLowerCase().includes('yes');
        conditionalBlock.style.display = isYes ? 'block' : 'none';

        this.updateProgress();
    },

    // ─── Select Exclusive Prof (mode EXCLUSIF) ──────────
    selectExclusiveProf(radio) {
        const moduleId = radio.dataset.module;
        const selectedProf = radio.value;

        // Cacher tous les blocs de profs pour ce module
        document.querySelectorAll(`.exclusive-prof-block[data-module-id="${moduleId}"]`).forEach(block => {
            block.style.display = 'none';
        });

        // Afficher le bloc du prof sélectionné
        if (selectedProf && selectedProf !== '__none__') {
            const block = document.querySelector(
                `.exclusive-prof-block[data-module-id="${moduleId}"][data-prof="${selectedProf}"]`
            );
            if (block) block.style.display = 'block';
        }

        this.updateProgress();
    },

    // ─── Collecte des réponses ──────────────────────────
    collectResponses() {
        const reponses = [];
        const form = document.getElementById('questionnaire-form');
        if (!form) return reponses;

        // Collecter les radios
        const radioGroups = new Set();
        form.querySelectorAll('input[type="radio"]:checked').forEach(r => {
            // Ignorer les radios exclusives de sélection de prof (valeur = nom de prof)
            if (r.name.includes('_exclusive_prof')) return;

            // Vérifier que le parent n'est pas hidden
            const block = r.closest('.question-block');
            if (block && block.closest('[style*="display: none"]')) return;

            const rep = {
                id_section: parseInt(r.dataset.section),
                id_question: parseInt(r.dataset.question),
                valeur: r.value,
            };
            if (r.dataset.module) rep.module_id = parseInt(r.dataset.module);
            if (r.dataset.prof) rep.enseignant = r.dataset.prof;
            reponses.push(rep);
        });

        // Collecter les checkboxes (regroupées par name)
        const checkboxGroups = {};
        form.querySelectorAll('input[type="checkbox"]:checked').forEach(c => {
            const block = c.closest('.question-block');
            if (block && block.closest('[style*="display: none"]')) return;

            const key = c.name;
            if (!checkboxGroups[key]) {
                checkboxGroups[key] = {
                    id_section: parseInt(c.dataset.section),
                    id_question: parseInt(c.dataset.question),
                    values: [],
                    module_id: c.dataset.module ? parseInt(c.dataset.module) : null,
                    enseignant: c.dataset.prof || null,
                };
            }
            checkboxGroups[key].values.push(c.value);
        });

        // Chaque valeur cochée = une ligne de réponse séparée
        for (const key of Object.keys(checkboxGroups)) {
            const group = checkboxGroups[key];
            for (const val of group.values) {
                const rep = {
                    id_section: group.id_section,
                    id_question: group.id_question,
                    valeur: val,
                };
                if (group.module_id) rep.module_id = group.module_id;
                if (group.enseignant) rep.enseignant = group.enseignant;
                reponses.push(rep);
            }
        }

        // Collecter les textareas
        form.querySelectorAll('textarea.open-answer').forEach(ta => {
            const block = ta.closest('.question-block');
            if (block && block.closest('[style*="display: none"]')) return;

            const val = ta.value.trim();
            if (!val) return; // Ignorer les vides

            const rep = {
                id_section: parseInt(ta.dataset.section),
                id_question: parseInt(ta.dataset.question),
                valeur: val,
            };
            if (ta.dataset.module) rep.module_id = parseInt(ta.dataset.module);
            if (ta.dataset.prof) rep.enseignant = ta.dataset.prof;
            reponses.push(rep);
        });

        return reponses;
    },

    // ─── Soumission ─────────────────────────────────────
    submit() {
        const reponses = this.collectResponses();

        if (reponses.length === 0) {
            alert("Veuillez répondre à au moins une question avant d'envoyer.");
            return;
        }

        const btn = document.getElementById('btn-submit');
        if (btn) {
            btn.disabled = true;
            btn.querySelector('.btn-submit-text').textContent = 'Envoi en cours...';
        }

        const { id_template, id_sondage } = window.__sondageData__;

        fetch(`/api/questionnaire/${id_template}/${id_sondage}/reponses`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reponses }),
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erreur serveur (${response.status})`);
                }
                return response.json();
            })
            .then(result => {
                // Cacher le formulaire et afficher la confirmation
                document.getElementById('questionnaire-form').style.display = 'none';
                document.querySelector('.questionnaire-hero').style.display = 'none';
                document.getElementById('confirmation-card').style.display = 'block';
            })
            .catch(error => {
                alert('Erreur lors de l\'envoi : ' + error.message);
                console.error(error);
                if (btn) {
                    btn.disabled = false;
                    btn.querySelector('.btn-submit-text').textContent = 'Envoyer les réponses';
                }
            });
    },
};

// ─── Init au chargement ─────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    Questionnaire.init();
});
