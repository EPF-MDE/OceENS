// ═══════════════════════════════════════════════════════
//  Questionnaire — Module JS
//  Logique conditionnelle, collecte, soumission
// ═══════════════════════════════════════════════════════

const Questionnaire = {

    // Mots-clés pour détecter SATISFAIT
    SATISFIED_KEYWORDS: ['très satisfait', 'very satisfied', 'plutôt satisfait', 'somewhat satisfied', 'totalement satisfait', 'totally satisfied'],

    // ─── Init ───────────────────────────────────────────
    init() {
        this.setupCheckboxLimits();
        this.setupProgressTracking();
        this.setupSequentialReveal();
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
        document.querySelectorAll('input[type="radio"]').forEach(el => {
            el.addEventListener('change', () => this.updateProgress());
        });
        document.querySelectorAll('textarea.open-answer').forEach(el => {
            el.addEventListener('input', () => this.updateProgress());
        });
    },

    // ─── Configurer la révélation séquentielle ──────────
    setupSequentialReveal() {
        // Écouter les réponses sur les questions intermédiaires pour révéler la suivante
        document.querySelectorAll('.question-block[data-q-role="middle"]').forEach(block => {
            const inputs = block.querySelectorAll('input[type="radio"], input[type="checkbox"]');
            const textarea = block.querySelector('textarea.open-answer');

            inputs.forEach(input => {
                input.addEventListener('change', () => {
                    this.revealNextQuestion(block);
                });
            });

            if (textarea) {
                textarea.addEventListener('input', () => {
                    if (textarea.value.trim().length > 0) {
                        this.revealNextQuestion(block);
                    }
                });
            }
        });
    },

    updateProgress() {
        const allBlocks = document.querySelectorAll('.question-block');
        const visibleBlocks = [];
        allBlocks.forEach(b => {
            if (!b.classList.contains('q-hidden') && !b.closest('[style*="display: none"]')) {
                visibleBlocks.push(b);
            }
        });
        const totalQuestions = visibleBlocks.length;
        if (totalQuestions === 0) return;

        let answered = 0;
        const radioGroups = new Set();
        visibleBlocks.forEach(b => {
            b.querySelectorAll('input[type="radio"]').forEach(r => radioGroups.add(r.name));
        });
        radioGroups.forEach(name => {
            if (document.querySelector(`input[name="${name}"]:checked`)) answered++;
        });

        const checkGroups = new Set();
        visibleBlocks.forEach(b => {
            b.querySelectorAll('input[type="checkbox"]').forEach(c => checkGroups.add(c.name));
        });
        checkGroups.forEach(name => {
            if (document.querySelector(`input[name="${name}"]:checked`)) answered++;
        });

        visibleBlocks.forEach(b => {
            const ta = b.querySelector('textarea.open-answer');
            if (ta && ta.value.trim().length > 0) answered++;
        });

        const percent = Math.round((answered / totalQuestions) * 100);
        const bar = document.getElementById('progress-bar');
        const text = document.getElementById('progress-text');
        if (bar) bar.style.width = percent + '%';
        if (text) text.textContent = percent + '% complété';
    },

    // ─── Logique de satisfaction ─────────────────────────
    // Appelé quand Q1 (satisfaction globale) est répondue
    handleSatisfaction(radio) {
        const value = radio.value.toLowerCase();
        const isSatisfied = this.SATISFIED_KEYWORDS.some(kw => value.includes(kw));

        // Trouver le groupe de satisfaction (section ou module-prof)
        const group = radio.closest('[data-satisfaction-group]');
        if (!group) return;

        const allBlocks = group.querySelectorAll('.question-block[data-q-role]');
        const middleBlocks = group.querySelectorAll('.question-block[data-q-role="middle"]');
        const lastBlock = group.querySelector('.question-block[data-q-role="last"]');

        if (isSatisfied) {
            // SATISFAIT : masquer les intermédiaires, afficher la dernière
            middleBlocks.forEach(b => {
                b.classList.add('q-hidden');
                b.classList.remove('q-visible');
                // Réinitialiser les réponses intermédiaires
                b.querySelectorAll('input[type="radio"]:checked').forEach(r => r.checked = false);
                b.querySelectorAll('input[type="checkbox"]:checked').forEach(c => c.checked = false);
                b.querySelectorAll('textarea').forEach(t => t.value = '');
            });
            if (lastBlock) {
                lastBlock.classList.remove('q-hidden');
                lastBlock.classList.add('q-visible');
            }
        } else {
            // INSATISFAIT : afficher Q2, masquer les suivants et la dernière
            if (lastBlock) {
                lastBlock.classList.add('q-hidden');
                lastBlock.classList.remove('q-visible');
                // Réinitialiser la dernière
                lastBlock.querySelectorAll('textarea').forEach(t => t.value = '');
            }

            let showNext = true;
            middleBlocks.forEach((b, idx) => {
                if (idx === 0) {
                    // Afficher la première question intermédiaire (Q2)
                    b.classList.remove('q-hidden');
                    b.classList.add('q-visible');
                } else {
                    // Masquer les suivantes, on les révèle séquentiellement
                    b.classList.add('q-hidden');
                    b.classList.remove('q-visible');
                    // Réinitialiser
                    b.querySelectorAll('input[type="radio"]:checked').forEach(r => r.checked = false);
                    b.querySelectorAll('input[type="checkbox"]:checked').forEach(c => c.checked = false);
                    b.querySelectorAll('textarea').forEach(t => t.value = '');
                }
            });
        }

        this.updateProgress();
    },

    // ─── Révéler la question suivante dans le mode séquentiel ──
    revealNextQuestion(currentBlock) {
        const group = currentBlock.closest('[data-satisfaction-group]');
        if (!group) return;

        const allMiddle = Array.from(group.querySelectorAll('.question-block[data-q-role="middle"]'));
        const currentIndex = allMiddle.indexOf(currentBlock);

        if (currentIndex >= 0 && currentIndex < allMiddle.length - 1) {
            const nextBlock = allMiddle[currentIndex + 1];
            if (nextBlock.classList.contains('q-hidden')) {
                nextBlock.classList.remove('q-hidden');
                nextBlock.classList.add('q-visible');
                // Scroll vers la question
                setTimeout(() => {
                    nextBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
            }
        }

        this.updateProgress();
    },

    // ─── Toggle UE Filter (UE optionnelle) ──────────────
    toggleUeFilter(radio) {
        const filterBlock = radio.closest('.ue-filter-block');
        if (!filterBlock) return;

        const ueCard = filterBlock.closest('.ue-group-card');
        if (!ueCard) return;

        const content = ueCard.querySelector('.ue-conditional-content');
        if (!content) return;

        const isYes = radio.value === 'Oui';
        content.style.display = isYes ? 'block' : 'none';

        // Réinitialiser les réponses si "Non"
        if (!isYes) {
            content.querySelectorAll('input[type="radio"]:checked').forEach(r => r.checked = false);
            content.querySelectorAll('input[type="checkbox"]:checked').forEach(c => c.checked = false);
            content.querySelectorAll('textarea').forEach(t => t.value = '');
        }

        this.updateProgress();
    },

    // ─── Toggle Prof Block (mode INCLUSIF) ──────────────
    toggleProfBlock(radio) {
        const profBlock = radio.closest('.prof-block-optional');
        if (!profBlock) return;

        const conditionalBlock = profBlock.querySelector('.prof-conditional-block');
        if (!conditionalBlock) return;

        const isYes = radio.value.toLowerCase().includes('oui') || radio.value.toLowerCase().includes('yes');
        conditionalBlock.style.display = isYes ? 'block' : 'none';

        if (!isYes) {
            conditionalBlock.querySelectorAll('input[type="radio"]:checked').forEach(r => r.checked = false);
            conditionalBlock.querySelectorAll('input[type="checkbox"]:checked').forEach(c => c.checked = false);
            conditionalBlock.querySelectorAll('textarea').forEach(t => t.value = '');
        }

        this.updateProgress();
    },

    // ─── Select Exclusive Prof (mode EXCLUSIF) ──────────
    selectExclusiveProf(radio) {
        const moduleId = radio.dataset.module;
        const selectedProf = radio.value;

        document.querySelectorAll(`.exclusive-prof-block[data-module-id="${moduleId}"]`).forEach(block => {
            block.style.display = 'none';
        });

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

        // Helper : vérifier si un élément est visible
        const isVisible = (el) => {
            const block = el.closest('.question-block');
            if (block && block.classList.contains('q-hidden')) return false;
            if (block && block.closest('[style*="display: none"]')) return false;
            return true;
        };

        // Collecter les radios
        form.querySelectorAll('input[type="radio"]:checked').forEach(r => {
            if (r.name.includes('_exclusive_prof')) return;
            if (r.name.startsWith('ue_filter_')) return;
            if (!isVisible(r)) return;

            const rep = {
                id_section: parseInt(r.dataset.section),
                id_question: parseInt(r.dataset.question),
                valeur: r.value,
            };
            if (r.dataset.module) rep.module_id = parseInt(r.dataset.module);
            if (r.dataset.prof) rep.enseignant = r.dataset.prof;
            reponses.push(rep);
        });

        // Collecter les checkboxes
        const checkboxGroups = {};
        form.querySelectorAll('input[type="checkbox"]:checked').forEach(c => {
            if (!isVisible(c)) return;
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
            if (!isVisible(ta)) return;
            const val = ta.value.trim();
            if (!val) return;
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
