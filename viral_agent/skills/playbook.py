"""Le savoir viral partagé par toutes les skills (injecté dans les prompts)."""

VIRAL_PLAYBOOK = """
RÈGLES D'UNE VIDÉO COURTE QUI PERCE (TikTok / Reels / Shorts) :
1. HOOK en < 2 secondes (≤ 12 mots). Il crée une tension immédiate : curiosité, choc, contradiction,
   enjeu personnel ("toi"), chiffre précis, ou promesse concrète. Jamais d'intro, jamais "Bonjour".
2. OPEN LOOP : annonce tôt qu'une révélation arrive ("et le 3e va te choquer", "attends la fin").
3. RYTHME : phrases courtes (5-12 mots), un nouvel élément toutes les 2-4 secondes (pattern interrupt).
4. SPÉCIFICITÉ : chiffres, noms, détails concrets > généralités. Une seule idée forte par vidéo.
5. ÉMOTION : surprise, peur de rater, fierté, colère légitime, émerveillement ou rire.
6. PAYOFF : tenir la promesse du hook. Le meilleur élément à la fin.
7. LOOP : la dernière phrase s'enchaîne naturellement avec la première (relecture = watch time).
8. CTA discret et spécifique (commenter un mot, partager à quelqu'un, suivre pour la partie 2).
9. Parler à l'oral, à la 2e personne, ton direct et assuré. Pas de jargon, pas de remplissage.
10. Durée idéale : 20-45 s (≈ 2,6 mots / seconde en voix off).

FORMATS QUI MARCHENT : "Personne ne te dit ça…", liste "3 choses…", mythe vs réalité, histoire vraie
avec twist, POV, avant/après, "Tu fais cette erreur…", fait incroyable, classement / countdown,
"Pourquoi X ? La vraie raison…", tutoriel express, secret d'initié.

VÉRACITÉ : chaque fait, chiffre ou nom doit être réel et vérifiable. N'invente JAMAIS une statistique.
Si tu n'es pas sûr d'un chiffre, formule sans chiffre. Une vidéo démontée en commentaires ne perce pas.

INTERDIT : fausses informations présentées comme vraies, contenu haineux, arnaques, promesses
financières mensongères, usurpation de personnes réelles.
"""

VISUAL_STYLES = {
    "cinematic": "cinematic film still, dramatic lighting, shallow depth of field, 35mm, highly detailed, vibrant colors",
    "anime": "anime key visual, studio quality, dynamic composition, vivid colors, detailed background",
    "realistic": "ultra realistic photo, natural light, sharp focus, 8k, professional photography",
    "dark": "dark moody cinematic, low key lighting, mysterious atmosphere, fog, high contrast",
    "3d": "3d render, pixar style, soft global illumination, colorful, cute, octane render",
    "comic": "bold comic book illustration, thick ink lines, halftone, dynamic angle, saturated colors",
    "minimal": "minimalist flat illustration, clean shapes, pastel palette, centered subject",
}

VOICES = {
    "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural", "young": "fr-FR-RemyMultilingualNeural"},
    "en": {"male": "en-US-AndrewNeural", "female": "en-US-AvaNeural", "young": "en-US-BrianNeural"},
    "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural", "young": "es-MX-JorgeNeural"},
    "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural", "young": "de-DE-FlorianMultilingualNeural"},
    "it": {"male": "it-IT-DiegoNeural", "female": "it-IT-ElsaNeural", "young": "it-IT-GiuseppeMultilingualNeural"},
    "pt": {"male": "pt-BR-AntonioNeural", "female": "pt-BR-FranciscaNeural", "young": "pt-BR-ThalitaMultilingualNeural"},
    "ar": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural", "young": "ar-EG-ShakirNeural"},
}

LANG_NAMES = {"fr": "français", "en": "English", "es": "español", "de": "Deutsch",
              "it": "italiano", "pt": "português", "ar": "العربية"}
