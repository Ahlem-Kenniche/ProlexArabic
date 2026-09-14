# -*- coding: utf-8 -*-
"""
Module de règles morphologiques pour les entités nommées arabes.
Basé sur regles_entites2_corrige.ipynb — Version corrigée avec la prof.

Pour chaque type, on distingue :
 - A. Instances (التصريف / الإعراب) : flexions selon le cas grammatical
 - B. Dérivés (الاشتقاق / النسبة) : adjectifs relationnels (nisba)

Pour chaque règle, on distingue trois statuts :
 - productive : forme générée automatiquement par une règle générale
 - lexicalisé : forme attestée stockée dans un lexique d'exceptions
 - non retenu dans cette version : traitement différé
"""
import re


# =============================================================================
# NORMALISATION ORTHOGRAPHIQUE
# =============================================================================

_ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670]")

def normaliser(mot):
    """
    Normalisation orthographique avant toute génération.
    1. Suppression des diacritiques (تشكيل / حركات)
    2. Suppression du tatweel (ـ)
    3. Strip espaces
    """
    mot = _ARABIC_DIACRITICS.sub("", mot)
    mot = mot.replace("ـ", "")
    return mot.strip()


# =============================================================================
# LEXIQUE D'EXCEPTIONS (Priorité 0 — absolue)
# =============================================================================

LEXIQUE_EXCEPTIONS = {
    "مكة": {
        "singulier_masculin": "مكّي",
        "singulier_feminin": "مكّية",
        "pluriel_masculin_nominatif": "مكّيون",
        "pluriel_masculin_oblique": "مكّيين",
        "pluriel_feminin": "مكّيات",
    },
    "آسيا": {
        "singulier_masculin": "آسيوي",
        "singulier_feminin": "آسيوية",
        "pluriel_masculin_nominatif": "آسيويون",
        "pluriel_masculin_oblique": "آسيويين",
        "pluriel_feminin": "آسيويات",
    },
    "صنعاء": {
        "singulier_masculin": "صنعاني",
        "singulier_feminin": "صنعانية",
        "pluriel_masculin_nominatif": "صنعانيون",
        "pluriel_masculin_oblique": "صنعانيين",
        "pluriel_feminin": "صنعانيات",
    },
    "بغداد": {
        "singulier_masculin": "بغدادي",
        "singulier_feminin": "بغدادية",
        "pluriel_masculin_nominatif": "بغداديون",
        "pluriel_masculin_oblique": "بغداديين",
        "pluriel_feminin": "بغداديات",
    },
    # Exception ville — insertion واو
    "حيفا": {
        "singulier_masculin": "حيفاوي",
        "singulier_feminin": "حيفاوية",
        "pluriel_masculin_nominatif": "حيفاويون",
        "pluriel_masculin_oblique": "حيفاويين",
        "pluriel_feminin": "حيفاويات",
    },
    # Exception pays — insertion واو
    "النمسا": {
        "singulier_masculin": "نمساوي",
        "singulier_feminin": "نمساوية",
        "pluriel_masculin_nominatif": "نمساويون",
        "pluriel_masculin_oblique": "نمساويين",
        "pluriel_feminin": "نمساويات",
    },
    # Ethnonymes irréguliers
    "الأكراد": {
        "singulier_masculin": "كردي",
        "singulier_feminin": "كردية",
        "pluriel_masculin_nominatif": "كرديون",
        "pluriel_masculin_oblique": "كرديين",
        "pluriel_feminin": "كرديات",
    },
    "الرومان": {
        "singulier_masculin": "روماني",
        "singulier_feminin": "رومانية",
        "pluriel_masculin_nominatif": "رومانيون",
        "pluriel_masculin_oblique": "رومانيين",
        "pluriel_feminin": "رومانيات",
    },
    "الفرس": {
        "singulier_masculin": "فارسي",
        "singulier_feminin": "فارسية",
        "pluriel_masculin_nominatif": "فارسيون",
        "pluriel_masculin_oblique": "فارسيين",
        "pluriel_feminin": "فارسيات",
    },
    "الأتراك": {
        "singulier_masculin": "تركي",
        "singulier_feminin": "تركية",
        "pluriel_masculin_nominatif": "تركيون",
        "pluriel_masculin_oblique": "تركيين",
        "pluriel_feminin": "تركيات",
    },
    "الآشوريون": {
        "singulier_masculin": "آشوري",
        "singulier_feminin": "آشورية",
        "pluriel_masculin_nominatif": "آشوريون",
        "pluriel_masculin_oblique": "آشوريين",
        "pluriel_feminin": "آشوريات",
    },
}


# =============================================================================
# DÉFINITION DES CATÉGORIES (38 types)
# =============================================================================

# Statuts possibles : "semi-productive", "productive", "lexicalisée", "non retenu v1"

CATEGORIES = {

    # =========================================================================
    # GÉOGRAPHIE — Toponymes et lieux
    # =========================================================================

    "pays": {
        "nom": "بلد",
        "nom_fr": "Pays",
        "description": "Noms de pays indépendants",
        "description_ar": "أسماء الدول المستقلة",
        "icone": "🌍",
        "a_derivation": True,
        "statut": "semi-productive",
        "exemples": ["فرنسا", "مصر", "اليابان", "سوريا", "الجزائر"],
        "placeholder": "مثال: فرنسا، الجزائر، مصر، سوريا ...",
    },
    "region": {
        "nom": "منطقة",
        "nom_fr": "Région",
        "description": "Territoire inclus dans un pays",
        "description_ar": "إقليم داخل دولة",
        "icone": "🗺️",
        "a_derivation": True,
        "statut": "semi-productive",
        "exemples": ["الأندلس", "الحجاز", "نجد", "كردستان", "البقاع"],
        "placeholder": "مثال: الأندلس، الحجاز، نجد ...",
    },
    "supranational": {
        "nom": "فوق وطني",
        "nom_fr": "Supranational",
        "description": "Territoires regroupant plusieurs pays — continents",
        "description_ar": "أقاليم تجمع عدة دول (قارات)",
        "icone": "🌐",
        "a_derivation": True,
        "statut": "semi-productive",
        "exemples": ["إفريقيا", "أوروبا", "آسيا", "أمريكا", "أقيانوسيا"],
        "placeholder": "مثال: إفريقيا، أوروبا، آسيا ...",
    },
    "territoire": {
        "nom": "إقليم",
        "nom_fr": "Territoire",
        "description": "Catégorie générale : Pays, Région ou Supranational",
        "description_ar": "فئة عامة: دولة أو منطقة أو فوق وطني",
        "icone": "📍",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["كردستان", "فلسطين"],
        "placeholder": "مثال: كردستان، فلسطين ...",
    },
    "ville": {
        "nom": "مدينة",
        "nom_fr": "Ville",
        "description": "Noms de villes",
        "description_ar": "أسماء المدن",
        "icone": "🏙️",
        "a_derivation": True,
        "statut": "semi-productive",
        "exemples": ["باريس", "القاهرة", "دمشق", "مكة", "القدس"],
        "placeholder": "مثال: باريس، دمشق، مكة، القاهرة ...",
    },
    "geonyme": {
        "nom": "جيونيم",
        "nom_fr": "Géonyme",
        "description": "Sites géographiques naturels",
        "description_ar": "مواقع جغرافية طبيعية (جبال، أودية، صحاري)",
        "icone": "⛰️",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["الأطلس", "الصحراء"],
        "placeholder": "مثال: الأطلس، الصحراء ...",
    },
    "hydronyme": {
        "nom": "هيدرونيم",
        "nom_fr": "Hydronyme",
        "description": "Étendues d'eau naturelles ou artificielles",
        "description_ar": "مسطحات مائية طبيعية أو اصطناعية",
        "icone": "🌊",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["النيل", "البحر الأحمر", "نهر دجلة"],
        "placeholder": "مثال: النيل، البحر الأحمر ...",
    },
    "voie": {
        "nom": "طريق",
        "nom_fr": "Voie",
        "description": "Rues, avenues, places, autoroutes",
        "description_ar": "طرق المرور والساحات والشوارع",
        "icone": "🛣️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["شارع النيل", "ساحة التحرير", "جادة الشانزليزيه"],
        "placeholder": "مثال: شارع النيل، ساحة التحرير ...",
    },
    "edifice": {
        "nom": "مبنى",
        "nom_fr": "Édifice",
        "description": "Bâtiments, monuments, lieux de culte",
        "description_ar": "مبانٍ مدنية أو دينية أو آثار",
        "icone": "🏛️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["الكعبة", "برج إيفل", "الأهرامات"],
        "placeholder": "مثال: الكعبة، برج إيفل ...",
    },
    "astronyme": {
        "nom": "فلكي",
        "nom_fr": "Astronyme",
        "description": "Objets célestes — planètes, étoiles, galaxies",
        "description_ar": "أجرام سماوية (كواكب، نجوم، مجرات)",
        "icone": "🪐",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["القمر", "الشمس"],
        "placeholder": "مثال: القمر، الشمس ...",
    },

    # =========================================================================
    # PERSONNES — Anthroponymes
    # =========================================================================

    "patronyme": {
        "nom": "لقب عائلي",
        "nom_fr": "Patronyme",
        "description": "Noms de famille",
        "description_ar": "أسماء العائلة والألقاب",
        "icone": "👨‍👩‍👧",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["هوغو", "نابليون", "بوتفليقة"],
        "placeholder": "مثال: هوغو، بوتفليقة ...",
    },
    "prenom": {
        "nom": "اسم شخصي",
        "nom_fr": "Prénom",
        "description": "Prénoms — classe flexionnelle = forme morphologique (schème), pas le type sémantique",
        "description_ar": "الأسماء الشخصية — التصنيف الصرفي يعتمد على الوزن لا على النوع الدلالي",
        "icone": "🏷️",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["محمد"],
        "placeholder": "مثال: محمد ...",
    },
    "pseudo_anthroponyme": {
        "nom": "اسم مستعار",
        "nom_fr": "Pseudo Anthroponyme",
        "description": "Noms d'animaux (zoonymes), personnages fictifs, pseudonymes",
        "description_ar": "أسماء حيوانات أو شخصيات خيالية أو أسماء مستعارة",
        "icone": "🎭",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["سندباد", "علاء الدين"],
        "placeholder": "مثال: سندباد، علاء الدين ...",
    },
    "celebrite": {
        "nom": "شخصية مشهورة",
        "nom_fr": "Célébrité",
        "description": "Personnalités célèbres et remarquables",
        "description_ar": "شخصيات مشهورة وبارزة",
        "icone": "⭐",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["أفلاطون", "ابن خلدون", "ابن سينا"],
        "placeholder": "مثال: أفلاطون، ابن خلدون ...",
    },
    "dynastie": {
        "nom": "سلالة / دولة",
        "nom_fr": "Dynastie",
        "description": "Noms de dynasties et maisons royales",
        "description_ar": "أسماء السلالات الحاكمة (جمع مذكر سالم) — أشكال معجمية",
        "icone": "👑",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["العباسيون", "الأمويون", "الفاطميون", "المرابطون"],
        "placeholder": "مثال: العباسيون، الأمويون ...",
    },
    "ethnonyme": {
        "nom": "اسم شعب",
        "nom_fr": "Ethnonyme",
        "description": "Noms de peuples et d'ethnies — formes lexicalisées",
        "description_ar": "أسماء الشعوب والأعراق — أشكال معجمية",
        "icone": "🌿",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["العرب", "الأمازيغ", "الأكراد", "الرومان", "الفرس", "الأتراك"],
        "placeholder": "مثال: العرب، الأمازيغ، الأكراد ...",
    },
    "individuel": {
        "nom": "فرد",
        "nom_fr": "Individuel",
        "description": "Un seul individu humain",
        "description_ar": "فرد واحد",
        "icone": "🧑",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["عمر", "خالد"],
        "placeholder": "مثال: عمر، خالد ...",
    },
    "collectif": {
        "nom": "جماعة",
        "nom_fr": "Collectif",
        "description": "Un groupe de personnes",
        "description_ar": "مجموعة من الأشخاص",
        "icone": "👥",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["قريش", "الأنصار", "المهاجرون"],
        "placeholder": "مثال: قريش، الأنصار ...",
    },
    "anthroponyme": {
        "nom": "أنثروبونيم",
        "nom_fr": "Anthroponyme",
        "description": "Supertype — regroupe Patronyme, Prénom, Célébrité, Dynastie, Ethnonyme, etc.",
        "description_ar": "نوع عام يجمع الأسماء المتعلقة بالبشر",
        "icone": "👤",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["محمد", "علي", "فاطمة"],
        "placeholder": "مثال: محمد، علي، فاطمة ...",
    },

    # =========================================================================
    # ORGANISATIONS — Ergonymes collectifs
    # =========================================================================

    "groupement": {
        "nom": "تجمع",
        "nom_fr": "Groupement",
        "description": "Entreprise, association, groupement",
        "description_ar": "شركة أو جمعية أو تجمع",
        "icone": "🏗️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["اتحاد المغرب العربي"],
        "placeholder": "مثال: اتحاد المغرب العربي ...",
    },
    "association": {
        "nom": "جمعية / حزب",
        "nom_fr": "Association",
        "description": "Associations ou partis politiques",
        "description_ar": "جمعيات أو أحزاب سياسية",
        "icone": "🤝",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["العفو الدولية", "حزب الله"],
        "placeholder": "مثال: العفو الدولية ...",
    },
    "ensemble": {
        "nom": "فرقة / نادي",
        "nom_fr": "Ensemble",
        "description": "Ensembles artistiques ou clubs sportifs",
        "description_ar": "فرق فنية أو أندية رياضية",
        "icone": "🎶",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["ريال مدريد", "الأهلي", "البيتلز"],
        "placeholder": "مثال: ريال مدريد، الأهلي ...",
    },
    "entreprise": {
        "nom": "شركة",
        "nom_fr": "Entreprise",
        "description": "Noms d'entreprise, groupe, firme",
        "description_ar": "أسماء الشركات والمؤسسات التجارية",
        "icone": "🏢",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["غوغل", "مايكروسوفت", "سوناطراك"],
        "placeholder": "مثال: غوغل، مايكروسوفت ...",
    },
    "institution": {
        "nom": "مؤسسة",
        "nom_fr": "Institution",
        "description": "Institutions publiques ou privées",
        "description_ar": "مؤسسات عمومية أو خاصة",
        "icone": "🏦",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["جامعة القاهرة", "البنك المركزي"],
        "placeholder": "مثال: جامعة القاهرة ...",
    },
    "organisation": {
        "nom": "منظمة",
        "nom_fr": "Organisation",
        "description": "Organisations internationales ou ONG",
        "description_ar": "منظمات دولية أو غير حكومية",
        "icone": "🌐",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["الأمم المتحدة", "أطباء بلا حدود", "اليونسكو"],
        "placeholder": "مثال: الأمم المتحدة، اليونسكو ...",
    },

    # =========================================================================
    # ÉVÉNEMENTS, OBJETS & IDÉES — Pragmonymes
    # =========================================================================

    "ergonyme": {
        "nom": "إرغونيم",
        "nom_fr": "Ergonyme",
        "description": "Fabrication humaine — trait concret",
        "description_ar": "صناعة بشرية — سمة ملموسة",
        "icone": "🔧",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["كلاشنيكوف", "كونكورد"],
        "placeholder": "مثال: كلاشنيكوف ...",
    },
    "pragmonyme": {
        "nom": "براغمونيم",
        "nom_fr": "Pragmonyme",
        "description": "Noms liés aux choses, objets et événements",
        "description_ar": "أسماء متعلقة بالأشياء والأحداث",
        "icone": "📎",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["نوبل", "أوسكار"],
        "placeholder": "مثال: نوبل، أوسكار ...",
    },
    "objet": {
        "nom": "شيء",
        "nom_fr": "Objet",
        "description": "Objet physique inanimé",
        "description_ar": "شيء مادي غير حي",
        "icone": "📦",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["إكسكاليبور", "الحجر الأسود"],
        "placeholder": "مثال: الحجر الأسود ...",
    },
    "produit": {
        "nom": "منتج / علامة تجارية",
        "nom_fr": "Produit",
        "description": "Marques et produits commerciaux",
        "description_ar": "علامات تجارية ومنتجات",
        "icone": "🛒",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["كوكاكولا", "نايك", "آبل"],
        "placeholder": "مثال: كوكاكولا، نايك، آبل ...",
    },
    "pensee": {
        "nom": "فكر / دين",
        "nom_fr": "Pensée",
        "description": "Religions, courants philosophiques et idéologiques",
        "description_ar": "أديان وتيارات فلسفية وأيديولوجية",
        "icone": "💭",
        "a_derivation": True,
        "statut": "lexicalisée",
        "exemples": ["الإسلام", "المسيحية", "الوجودية", "الشيوعية"],
        "placeholder": "مثال: الإسلام، المسيحية ...",
    },
    "vaisseau": {
        "nom": "مركبة / سفينة",
        "nom_fr": "Vaisseau",
        "description": "Bateaux, vaisseaux spatiaux, navires",
        "description_ar": "سفن وناقلات ومركبات فضائية",
        "icone": "🚀",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["التيتانيك", "أبولو", "تشالنجر"],
        "placeholder": "مثال: التيتانيك، تشالنجر ...",
    },
    "oeuvre": {
        "nom": "عمل فني / أدبي",
        "nom_fr": "Œuvre",
        "description": "Œuvres littéraires et artistiques",
        "description_ar": "أعمال أدبية وفنية",
        "icone": "🎨",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["ألف ليلة وليلة", "كليلة ودمنة"],
        "placeholder": "مثال: ألف ليلة وليلة ...",
    },
    "catastrophe": {
        "nom": "كارثة",
        "nom_fr": "Catastrophe",
        "description": "Événements catastrophiques naturels ou humains",
        "description_ar": "أحداث كارثية طبيعية أو بشرية",
        "icone": "⚠️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["زلزال أغادير", "كارثة تشيرنوبيل"],
        "placeholder": "مثال: زلزال أغادير ...",
    },
    "manifestation": {
        "nom": "فعالية",
        "nom_fr": "Manifestation",
        "description": "Manifestations sportives ou culturelles",
        "description_ar": "فعاليات رياضية أو ثقافية",
        "icone": "🎪",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["الألعاب الأولمبية", "مهرجان كان"],
        "placeholder": "مثال: الألعاب الأولمبية ...",
    },
    "fete": {
        "nom": "عيد / احتفال",
        "nom_fr": "Fête",
        "description": "Événements festifs récurrents",
        "description_ar": "مناسبات احتفالية متكررة",
        "icone": "🎉",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["عيد الأضحى", "رمضان", "عيد الفطر"],
        "placeholder": "مثال: عيد الأضحى، رمضان ...",
    },
    "histoire": {
        "nom": "حدث تاريخي",
        "nom_fr": "Histoire",
        "description": "Événements historiques marquants",
        "description_ar": "أحداث تاريخية بارزة",
        "icone": "📜",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["الثورة الفرنسية", "ثورة نوفمبر"],
        "placeholder": "مثال: الثورة الفرنسية، ثورة نوفمبر ...",
    },
    "meteorologie": {
        "nom": "ظاهرة جوية",
        "nom_fr": "Météorologie",
        "description": "Phénomènes météorologiques nommés",
        "description_ar": "ظواهر جوية ومناخية مسماة",
        "icone": "🌪️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": ["إعصار كاترينا", "النينو"],
        "placeholder": "مثال: إعصار كاترينا، النينو ...",
    },

    # =========================================================================
    # SUPERTYPES (regroupements)
    # =========================================================================

    "toponyme": {
        "nom": "طوبونيم",
        "nom_fr": "Toponyme",
        "description": "Supertype — regroupe Pays, Région, Supranational, Territoire, Ville, etc.",
        "description_ar": "نوع عام يجمع الأسماء المتعلقة بالأماكن",
        "icone": "🗺️",
        "a_derivation": False,
        "statut": "non retenu v1",
        "exemples": [],
        "placeholder": "أدخل اسم مكان ...",
    },
}


# Groupes thématiques pour organisation de l'interface
GROUPES = {
    "🌍 Géographie": [
        "pays", "region", "supranational", "territoire",
        "ville", "geonyme", "hydronyme", "voie", "edifice", "astronyme",
    ],
    "👥 Personnes": [
        "patronyme", "prenom", "pseudo_anthroponyme", "celebrite",
        "ethnonyme", "dynastie", "individuel", "collectif", "anthroponyme",
    ],
    "🏢 Organisations": [
        "groupement", "association", "ensemble",
        "entreprise", "institution", "organisation",
    ],
    "📅 Événements & Objets": [
        "ergonyme", "pragmonyme", "objet",
        "produit", "oeuvre", "manifestation", "histoire",
        "pensee", "fete", "vaisseau", "catastrophe", "meteorologie",
    ],
}


# =============================================================================
# DICTIONNAIRE DE NORMALISATION (Règle P-4 / D-3 — Noms composés)
# =============================================================================

MOTS_COMPOSES = {
    "المملكة العربية السعودية": "السعود",
    "الولايات المتحدة الأمريكية": "أمريكا",
    "الولايات المتحدة": "أمريكا",
    "جنوب أفريقيا": "أفريقيا",
    "المملكة المتحدة": "بريطانيا",
    "الإمارات العربية المتحدة": "الإمارات",
    "أبو ظبي": "ظبي",
}


# =============================================================================
# CONTINENTS (Supranational — dérivation spéciale)
# =============================================================================

CONTINENTS_SPECIAUX = {
    "شمال إفريقيا": {
        "singulier_masculin": "شمال أفريقي",
        "singulier_feminin": "شمال أفريقية",
        "pluriel_masculin_nominatif": "شمال أفريقيون",
        "pluriel_masculin_oblique": "شمال أفريقيين",
        "pluriel_feminin": "شمال أفريقيات",
    },
}
# Note : آسيا est dans LEXIQUE_EXCEPTIONS car c'est un cas irrégulier/lexicalisé


# =============================================================================
# LISTES DE MOTS CONCERNÉS PAR LES RÈGLES DE DÉRIVATION
# =============================================================================
# Principe : seuls les mots figurant dans ces listes sont soumis aux règles.
# Si un mot n'est pas dans la liste, aucune dérivation n'est générée.

PAYS_AVEC_DERIVATION = frozenset({
    # P-1 — Terminaison ا
    "فرنسا", "كندا", "كوبا", "أمريكا", "هولندا", "بولندا", "أيرلندا", "نيوزيلندا",
    "سويسرا", "أنغولا", "أوغندا", "رواندا", "غانا", "بنما", "كوستاريكا", "فنزويلا",
    "نيكاراغوا", "بلجيكا", "أندورا",
    # P-2 — Terminaison ان
    "لبنان", "اليابان", "السودان", "عمان", "إيران", "أفغانستان", "باكستان",
    "كازاخستان", "أوزبكستان", "تركمانستان", "طاجيكستان", "قيرغيزستان", "أذربيجان",
    # P-3 — Terminaison يا
    "ليبيا", "سوريا", "تركيا", "ألمانيا", "إيطاليا", "بريطانيا", "روسيا",
    "ماليزيا", "إندونيسيا", "نيجيريا", "كولومبيا", "بوليفيا", "إثيوبيا",
    "كينيا", "تنزانيا", "كمبوديا", "منغوليا", "رومانيا", "بلغاريا", "صربيا",
    "كرواتيا", "سلوفاكيا", "سلوفينيا", "لاتفيا", "ليتوانيا", "إستونيا",
    "ألبانيا", "جورجيا", "أرمينيا", "أستراليا", "موريتانيا", "إريتريا",
    "ليبيريا", "غينيا", "زامبيا", "نامبيا", "غامبيا", "إسبانيا", "أوكرانيا", "مقدونيا",
    # P-4 — Composés
    "المملكة العربية السعودية", "الولايات المتحدة الأمريكية", "الولايات المتحدة",
    "جنوب أفريقيا", "المملكة المتحدة", "الإمارات العربية المتحدة", "أبو ظبي",
    # P-5 — Terminaison consonantique
    "مصر", "قطر", "المغرب", "الجزائر", "تونس", "العراق", "الأردن", "اليمن",
    "الكويت", "البحرين", "فلسطين", "الصومال", "السنغال", "تشاد", "النيجر",
    "المكسيك", "البرازيل", "الهند", "الصين", "الأرجنتين", "الفلبين", "النرويج",
    # Exceptions (P-0)
    "النمسا",
})

SUPRANATIONAL_AVEC_DERIVATION = frozenset({
    "إفريقيا", "أمريكا", "آسيا", "أوروبا", "أقيانوسيا",
    "شمال إفريقيا",
})

VILLES_AVEC_DERIVATION = frozenset({
    # V-0 — Exceptions
    "مكة", "صنعاء", "بغداد", "حيفا",
    # V-1 — Terminaison ة
    "القاهرة", "جدة", "المدينة", "الدوحة", "الشارقة", "عنابة", "قسنطينة",
    "بجاية", "سبتة", "طنجة", "الإسكندرية", "البصرة", "غزة", "أنقرة",
    "المنامة", "الحديدة", "اللاذقية", "مليلة",
    # V-2 — Terminaison ا
    "يافا", "صيدا", "عكا",
    # V-3 — Avec ال (sans ة)
    "القدس", "الرياض", "الخرطوم", "الرباط", "الموصل", "الخليل",
    # V-4 — Terminaison consonantique
    "دمشق", "تونس", "بيروت", "حلب",
    "مراكش", "فاس", "عمّان", "حمص", "نابلس", "طرابلس", "وهران",
    # Composés
    "أبو ظبي",
})

DYNASTIES_AVEC_DERIVATION = frozenset({
    # Pluriel masculin sain (ون)
    "العباسيون", "الأمويون", "الفاطميون", "المرابطون", "الموحدون",
    "الزيانيون", "الحفصيون", "الأيوبيون", "الرستميون", "الإدريسيون",
    "المرينيون", "الحمّاديون", "الحماديون", "العثمانيون", "الصفويون",
    "البويهيون", "الغزنويون", "السامانيون", "الطولونيون", "الإخشيديون",
    "الوطاسيون", "السعديون", "العلويون", "النوميديون",
    # Formes en ين (accusatif/génitif)
    "العباسيين", "الأمويين", "الفاطميين", "المرابطين", "الموحدين",
    "الزيانيين", "الحفصيين", "الأيوبيين", "الرستميين", "الإدريسيين",
    "المرينيين", "الحمّاديين", "الحماديين", "العثمانيين", "الصفويين",
    "البويهيين", "الغزنويين", "السامانيين", "الطولونيين", "الإخشيديين",
    "الوطاسيين", "السعديين", "العلويين", "النوميديين",
    # Pluriels irréguliers (جمع تكسير)
    "الأغالبة", "السلاجقة", "المماليك",
})

ETHNONYMES_AVEC_DERIVATION = frozenset({
    "العرب", "الأمازيغ", "الأكراد", "الرومان", "الفرس", "الأتراك",
    "التركمان", "القبط", "اليهود", "الأرمن", "الشركس", "السريان",
    "الآشوريون", "الكلدان", "البلوش", "الطوارق", "النوبيون",
})

# Régions avec nisba attestée — formes irrégulières dans LEXIQUE_REGIONS
LEXIQUE_REGIONS = {
    "الصحراء": {
        "singulier_masculin": "صحراوي",
        "singulier_feminin": "صحراوية",
        "pluriel_masculin_nominatif": "صحراويون",
        "pluriel_masculin_oblique": "صحراويين",
        "pluriel_feminin": "صحراويات",
    },
    "سيناء": {
        "singulier_masculin": "سينائي",
        "singulier_feminin": "سينائية",
        "pluriel_masculin_nominatif": "سينائيون",
        "pluriel_masculin_oblique": "سينائيين",
        "pluriel_feminin": "سينائيات",
    },
    "الأحساء": {
        "singulier_masculin": "أحسائي",
        "singulier_feminin": "أحسائية",
        "pluriel_masculin_nominatif": "أحسائيون",
        "pluriel_masculin_oblique": "أحسائيين",
        "pluriel_feminin": "أحسائيات",
    },
}

REGIONS_AVEC_DERIVATION = frozenset({
    # Attestés avec nisba documentée — défaut (P-5 : strip ال + ي)
    "الأندلس", "الحجاز", "نجد", "الجليل", "البقاع",
    "عسير", "ظفار", "تهامة",
    # Attestés — irréguliers (stockés dans LEXIQUE_REGIONS)
    "الصحراء", "سيناء", "الأحساء",
    # Attestés — règle ان (كردستاني)
    "كردستان",
})


# =============================================================================
# GÉONYMES — formes lexicalisées (Nisba documentée)
# =============================================================================

LEXIQUE_GEONYMES = {
    "الأطلس": {
        "singulier_masculin": "أطلسي",
        "singulier_feminin": "أطلسية",
        "pluriel_masculin_nominatif": "أطلسيون",
        "pluriel_masculin_oblique": "أطلسيين",
        "pluriel_feminin": "أطلسيات",
    },
    "الصحراء": {
        "singulier_masculin": "صحراوي",
        "singulier_feminin": "صحراوية",
        "pluriel_masculin_nominatif": "صحراويون",
        "pluriel_masculin_oblique": "صحراويين",
        "pluriel_feminin": "صحراويات",
    },
}

GEONYMES_AVEC_DERIVATION = frozenset({
    "الأطلس", "الصحراء",
})


# =============================================================================
# ASTRONYMES — formes lexicalisées (Nisba documentée)
# =============================================================================

LEXIQUE_ASTRONYMES = {
    "القمر": {
        "singulier_masculin": "قمري",
        "singulier_feminin": "قمرية",
        "pluriel_masculin_nominatif": "قمريون",
        "pluriel_masculin_oblique": "قمريين",
        "pluriel_feminin": "قمريات",
    },
    "الشمس": {
        "singulier_masculin": "شمسي",
        "singulier_feminin": "شمسية",
        "pluriel_masculin_nominatif": "شمسيون",
        "pluriel_masculin_oblique": "شمسيين",
        "pluriel_feminin": "شمسيات",
    },
}

ASTRONYMES_AVEC_DERIVATION = frozenset({
    "القمر", "الشمس",
})


# =============================================================================
# PRÉNOMS — formes lexicalisées (Nisba documentée)
# =============================================================================

LEXIQUE_PRENOMS = {
    "محمد": {
        "singulier_masculin": "محمدي",
        "singulier_feminin": "محمدية",
        "pluriel_masculin_nominatif": "محمديون",
        "pluriel_masculin_oblique": "محمديين",
        "pluriel_feminin": "محمديات",
    },
}

PRENOMS_AVEC_DERIVATION = frozenset({
    "محمد",
})


# =============================================================================
# PENSÉE — religions, idéologies, courants philosophiques
# Nisba lexicalisée — forme simple générée par règle sur la base
# =============================================================================

PENSEES_AVEC_DERIVATION = frozenset({
    "الإسلام", "المسيحية", "اليهودية", "البوذية",
    "الشيوعية", "الوجودية", "الرأسمالية", "الاشتراكية",
    "الليبرالية", "القومية", "العلمانية",
})


# =============================================================================
# MOTEUR DE RÈGLES
# =============================================================================

def _resultat_vide():
    return {
        "singulier_masculin": "",
        "singulier_feminin": "",
        "pluriel_masculin_nominatif": "",
        "pluriel_masculin_oblique": "",
        "pluriel_feminin": "",
    }


def _supprimer_article(mot):
    """Supprime l'article défini ال du début du mot si présent."""
    if mot.startswith("ال"):
        return mot[2:]
    return mot


def _mot_dans_liste(mot, liste):
    """Vérifie si un mot (normalisé) appartient à la liste autorisée.
    Teste le mot tel quel, sans ال, et avec ال."""
    if mot in liste:
        return True
    sans_al = _supprimer_article(mot)
    if sans_al in liste:
        return True
    if "ال" + mot in liste:
        return True
    return False


# -----------------------------------------------------------------------------
# Règles PAYS — P-1 à P-5
# -----------------------------------------------------------------------------

def _appliquer_nisba_direct(mot):
    """Applique les règles de Nisba directement, sans vérification de liste.
    Utilisé pour les mots racines extraits de noms composés (règle P-4/D-3)."""
    mot = normaliser(mot).strip()
    if mot in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[mot], f"Exception lexicalisée pour « {mot} »"
    base = _supprimer_article(mot)
    if base in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[base], f"Exception lexicalisée pour « {base} »"
    r, e = regle_P3_ya(base)
    if r:
        return r, e
    r, e = regle_P1_alif(base)
    if r:
        return r, e
    r, e = regle_P2_ain(base)
    if r:
        return r, e
    return regle_P5_consonne(mot)


def regle_P1_alif(mot):
    """Règle P-1 : Pays finissant par ا (Alif). Ex: فرنسا → فرنسي"""
    if not mot.endswith("ا"):
        return None, None
    racine = mot[:-1]
    return {
        "singulier_masculin": racine + "ي",
        "singulier_feminin": racine + "ية",
        "pluriel_masculin_nominatif": racine + "يون",
        "pluriel_masculin_oblique": racine + "يين",
        "pluriel_feminin": racine + "يات",
    }, "Règle P-1 — Terminaison ا (Alif) : on remplace ا par les suffixes de Nisba"


def regle_P2_ain(mot):
    """Règle P-2 : Pays finissant par ان. Ex: اليابان → ياباني"""
    if not mot.endswith("ان"):
        return None, None
    return {
        "singulier_masculin": mot + "ي",
        "singulier_feminin": mot + "ية",
        "pluriel_masculin_nominatif": mot + "يون",
        "pluriel_masculin_oblique": mot + "يين",
        "pluriel_feminin": mot + "يات",
    }, "Règle P-2 — Terminaison ان : on ajoute les suffixes de Nisba directement"


def regle_P3_ya(mot):
    """Règle P-3 : Pays finissant par يا. Ex: سوريا → سوري"""
    if not mot.endswith("يا"):
        return None, None
    racine = mot[:-2]
    return {
        "singulier_masculin": racine + "ي",
        "singulier_feminin": racine + "ية",
        "pluriel_masculin_nominatif": racine + "يون",
        "pluriel_masculin_oblique": racine + "يين",
        "pluriel_feminin": racine + "يات",
    }, "Règle P-3 — Terminaison يا : on remplace يا par les suffixes de Nisba"


def regle_P4_compose(mot):
    """Règle P-4 (D-3) : Mots composés → normalisation par mot racine."""
    mot_racine = MOTS_COMPOSES.get(mot.strip())
    if not mot_racine:
        return None, None
    resultat, sous_regle = _appliquer_nisba_direct(mot_racine)
    explication = f"Règle P-4 — Nom composé : extraction du mot racine « {mot_racine} » puis {sous_regle}"
    return resultat, explication


def regle_P5_consonne(mot):
    """Règle P-5 (D-2) : Pays finissant par consonne (défaut). Ex: مصر → مصري"""
    base = _supprimer_article(mot)
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, "Règle P-5 — Terminaison consonne (défaut) : on ajoute directement les suffixes"


def appliquer_regles_pays(mot):
    """
    Applique les règles de Nisba sur un nom de pays.
    Ordre de priorité : Exceptions → P-4 → P-3 → P-1 → P-2 → P-5
    Seuls les pays figurant dans PAYS_AVEC_DERIVATION sont traités.
    """
    mot = normaliser(mot).strip()

    # Vérifier que le mot est dans la liste des pays concernés
    if not _mot_dans_liste(mot, PAYS_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des pays concernés par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    # Priorité 0 : lexique d'exceptions
    norm = _supprimer_article(mot)
    if mot in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[mot], f"Exception lexicalisée — forme attestée pour « {mot} »"
    if norm in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[norm], f"Exception lexicalisée — forme attestée pour « {norm} »"

    # Priorité 1 : mots composés (P-4)
    r, e = regle_P4_compose(mot)
    if r:
        return r, e

    # Supprimer l'article pour l'analyse de la terminaison
    base = _supprimer_article(mot)

    # Priorité 2 : يا (P-3, avant P-1 car يا se termine aussi par ا)
    r, e = regle_P3_ya(base)
    if r:
        return r, e

    # Priorité 3 : ا (P-1)
    r, e = regle_P1_alif(base)
    if r:
        return r, e

    # Priorité 4 : ان (P-2)
    r, e = regle_P2_ain(base)
    if r:
        return r, e

    # Priorité 5 : consonne (P-5, défaut)
    return regle_P5_consonne(mot)


# -----------------------------------------------------------------------------
# Règle SUPRANATIONAL (Continents)
# -----------------------------------------------------------------------------

def appliquer_regles_supranational(mot):
    """Appliquer les règles de dérivation pour les continents."""
    mot = normaliser(mot).strip()

    # Vérifier que le mot est dans la liste des supranationaux concernés
    if not _mot_dans_liste(mot, SUPRANATIONAL_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des entités supranationales concernées "
            f"par les règles de dérivation. Le mot est retourné sans modification."
        )

    # Priorité 0 : lexique d'exceptions (آسيا)
    if mot in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[mot], f"Exception lexicalisée — cas irrégulier pour « {mot} »"

    # Cas spéciaux composés (شمال إفريقيا)
    if mot in CONTINENTS_SPECIAUX:
        return CONTINENTS_SPECIAUX[mot], f"Continent composé : dérivation spéciale pour « {mot} »"

    # Autres continents → appliquer les mêmes règles que les pays
    base = _supprimer_article(mot)
    r, e = regle_P3_ya(base)
    if r:
        return r, f"Continent : {e}"
    r, e = regle_P1_alif(base)
    if r:
        return r, f"Continent : {e}"
    return regle_P5_consonne(mot)


# -----------------------------------------------------------------------------
# Règles VILLE — V-0 à V-4
# -----------------------------------------------------------------------------

def appliquer_regles_ville(mot):
    """
    Règles de dérivation (Nisba) pour les villes.
    Ordre : V-0 (exceptions) → V-1 (ة) → V-2 (ا/يا) → V-3/V-4 (consonne)
    Seules les villes figurant dans VILLES_AVEC_DERIVATION sont traitées.
    """
    mot = normaliser(mot).strip()

    # Vérifier que le mot est dans la liste des villes concernées
    if not _mot_dans_liste(mot, VILLES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des villes concernées par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    # V-0 : Exceptions lexicalisées (priorité absolue)
    base_check = _supprimer_article(mot)
    if mot in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[mot], f"Règle V-0 — Exception lexicalisée pour « {mot} »"
    if base_check in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[base_check], f"Règle V-0 — Exception lexicalisée pour « {base_check} »"

    # Composés de villes
    pivot = MOTS_COMPOSES.get(mot)
    if pivot:
        if pivot in LEXIQUE_EXCEPTIONS:
            return LEXIQUE_EXCEPTIONS[pivot], f"Règle V-0 — Ville composée « {mot} » → pivot « {pivot} » (lexicalisé)"
        base_p = _supprimer_article(pivot)
        return {
            "singulier_masculin": base_p + "ي",
            "singulier_feminin": base_p + "ية",
            "pluriel_masculin_nominatif": base_p + "يون",
            "pluriel_masculin_oblique": base_p + "يين",
            "pluriel_feminin": base_p + "يات",
        }, f"Ville composée « {mot} » → pivot « {pivot} » puis suffixes"

    base = _supprimer_article(mot)

    # V-1 : ta marbuta ة
    if base.endswith("ة"):
        racine = base[:-1]
        return {
            "singulier_masculin": racine + "ي",
            "singulier_feminin": racine + "ية",
            "pluriel_masculin_nominatif": racine + "يون",
            "pluriel_masculin_oblique": racine + "يين",
            "pluriel_feminin": racine + "يات",
        }, "Règle V-1 — Terminaison ة (ta marbuta) : on supprime ة puis on ajoute les suffixes de Nisba"

    # V-2 : يا (avant ا)
    r, e = regle_P3_ya(base)
    if r:
        return r, f"Règle V-2 — {e}"

    # V-2 : ا
    r, e = regle_P1_alif(base)
    if r:
        return r, f"Règle V-2 — {e}"

    # V-3 / V-4 : consonne (avec ou sans ال)
    label = "Règle V-3" if mot.startswith("ال") else "Règle V-4"
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, f"{label} — Terminaison consonne : on ajoute directement les suffixes de Nisba"


# -----------------------------------------------------------------------------
# DYNASTIE et ETHNONYME — formes lexicalisées
# -----------------------------------------------------------------------------

def appliquer_regles_dynastie(mot):
    """
    DYNASTIE : les formes sont lexicalisées (nisba déjà existante).
    Extraction du singulier à partir du pluriel ون/ين.
    Seules les dynasties figurant dans DYNASTIES_AVEC_DERIVATION sont traitées.
    """
    mot = normaliser(mot).strip()

    # Vérifier que le mot est dans la liste des dynasties concernées
    if not _mot_dans_liste(mot, DYNASTIES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des dynasties concernées par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    base = _supprimer_article(mot)

    if base.endswith("ون"):
        racine_pl = base[:-2]
        return {
            "singulier_masculin": racine_pl,
            "singulier_feminin": racine_pl + "ة",
            "pluriel_masculin_nominatif": racine_pl + "ون",
            "pluriel_masculin_oblique": racine_pl + "ين",
            "pluriel_feminin": racine_pl + "ات",
        }, "Dynastie (lexicalisé) — singulier extrait du pluriel sain, alternance ون ↔ ين"

    if base.endswith("ين"):
        racine_pl = base[:-2]
        return {
            "singulier_masculin": racine_pl,
            "singulier_feminin": racine_pl + "ة",
            "pluriel_masculin_nominatif": racine_pl + "ون",
            "pluriel_masculin_oblique": racine_pl + "ين",
            "pluriel_feminin": racine_pl + "ات",
        }, "Dynastie (lexicalisé) — singulier extrait du pluriel sain, alternance ون ↔ ين"

    # Forme non reconnue comme pluriel sain (جمع تكسير comme الأغالبة)
    # Appliquer suffixation directe sur la base
    base = _supprimer_article(mot)
    if base.endswith("ة"):
        racine = base[:-1]
        return {
            "singulier_masculin": racine + "ي",
            "singulier_feminin": racine + "ية",
            "pluriel_masculin_nominatif": racine + "يون",
            "pluriel_masculin_oblique": racine + "يين",
            "pluriel_feminin": racine + "يات",
        }, "Dynastie (جمع تكسير) — suffixation après suppression de ة"
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, "Dynastie — suffixation directe"


def appliquer_regles_ethnonyme(mot):
    """
    ETHNONYME : formes en général lexicalisées.
    On vérifie le lexique d'exceptions d'abord, puis on applique les règles pays.
    Seuls les ethnonymes figurant dans ETHNONYMES_AVEC_DERIVATION sont traités.
    """
    mot = normaliser(mot).strip()

    # Vérifier que le mot est dans la liste des ethnonymes concernés
    if not _mot_dans_liste(mot, ETHNONYMES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des ethnonymes concernés par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    # Priorité 0 : lexique d'exceptions
    if mot in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[mot], f"Ethnonyme (lexicalisé) — forme attestée pour « {mot} »"
    base = _supprimer_article(mot)
    if base in LEXIQUE_EXCEPTIONS:
        return LEXIQUE_EXCEPTIONS[base], f"Ethnonyme (lexicalisé) — forme attestée"

    # Sinon, appliquer les règles de suffixation directement
    base = _supprimer_article(mot)
    # يا
    r, e = regle_P3_ya(base)
    if r:
        return r, f"Ethnonyme — {e}"
    # ا
    r, e = regle_P1_alif(base)
    if r:
        return r, f"Ethnonyme — {e}"
    # ان
    r, e = regle_P2_ain(base)
    if r:
        return r, f"Ethnonyme — {e}"
    # défaut (consonne)
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, f"Ethnonyme — Règle par défaut : suffixation directe sur « {base} »"


def appliquer_regles_region(mot):
    """
    RÉGION : dérivation par lexique (irréguliers) puis règles P-1/P-2/P-3/P-5.
    Seules les régions figurant dans REGIONS_AVEC_DERIVATION sont traitées.
    """
    mot = normaliser(mot).strip()

    if not _mot_dans_liste(mot, REGIONS_AVEC_DERIVATION):
        return None, (
            f"Région : aucune dérivation documentée pour ce nom dans cette version. "
            f"Les formes éventuelles seront traitées dans une version ultérieure."
        )

    # Priorité R-0 : lexique des formes irrégulières de régions
    for cle in [mot, _supprimer_article(mot)]:
        if cle in LEXIQUE_REGIONS:
            return LEXIQUE_REGIONS[cle], f"Règle R-0 — Exception lexicalisée : forme irrégulière attestée pour « {mot} »"
    for cle in [mot, _supprimer_article(mot)]:
        if "ال" + cle in LEXIQUE_REGIONS:
            return LEXIQUE_REGIONS["ال" + cle], f"Règle R-0 — Exception lexicalisée : forme irrégulière attestée pour « {mot} »"

    base = _supprimer_article(mot)

    # Règle R-1 : Terminaison يا
    r, e = regle_P3_ya(base)
    if r:
        return r, f"Règle R-1 — Terminaison يا : suppression de يا + suffixes de Nisba sur « {base[:-2] if base.endswith('يا') else base} »"
    # Règle R-2 : Terminaison ا
    r, e = regle_P1_alif(base)
    if r:
        return r, f"Règle R-2 — Terminaison ا : suppression de ا + suffixes de Nisba sur « {base[:-1] if base.endswith('ا') else base} »"
    # Règle R-3 : Terminaison ان (ex. كردستان → كردستاني)
    r, e = regle_P2_ain(base)
    if r:
        return r, f"Règle R-3 — Terminaison ان : ajout direct des suffixes de Nisba sur « {base} »"
    # Règle R-4 : Terminaison ة (ex. تهامة → تهامي)
    if base.endswith("ة"):
        racine = base[:-1]
        return {
            "singulier_masculin": racine + "ي",
            "singulier_feminin": racine + "ية",
            "pluriel_masculin_nominatif": racine + "يون",
            "pluriel_masculin_oblique": racine + "يين",
            "pluriel_feminin": racine + "يات",
        }, f"Règle R-4 — Terminaison ة (ta marbuta) : suppression de ة + suffixes de Nisba sur « {racine} »"
    # Règle R-5 : Défaut consonantique (ex. الأندلس → أندلسي, الحجاز → حجازي)
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, f"Règle R-5 — Terminaison consonantique (défaut) : suppression de ال (si présent) + suffixes de Nisba sur « {base} »"


# -----------------------------------------------------------------------------
# Règles GÉONYME — formes lexicalisées
# -----------------------------------------------------------------------------

def appliquer_regles_geonyme(mot):
    """
    GÉONYME : formes lexicalisées uniquement.
    Seuls les géonymes figurant dans GEONYMES_AVEC_DERIVATION sont traités.
    """
    mot = normaliser(mot).strip()

    if not _mot_dans_liste(mot, GEONYMES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des géonymes concernés par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    for cle in [mot, _supprimer_article(mot)]:
        if cle in LEXIQUE_GEONYMES:
            return LEXIQUE_GEONYMES[cle], f"Géonyme (lexicalisé) — forme attestée pour « {mot} »"
    for cle in [mot, _supprimer_article(mot)]:
        if "ال" + cle in LEXIQUE_GEONYMES:
            return LEXIQUE_GEONYMES["ال" + cle], f"Géonyme (lexicalisé) — forme attestée pour « {mot} »"

    return None, f"Géonyme : aucune forme documentée pour « {mot} »."


# -----------------------------------------------------------------------------
# Règles ASTRONYME — formes lexicalisées
# -----------------------------------------------------------------------------

def appliquer_regles_astronyme(mot):
    """
    ASTRONYME : formes lexicalisées uniquement.
    Seuls les astronymes figurant dans ASTRONYMES_AVEC_DERIVATION sont traités.
    """
    mot = normaliser(mot).strip()

    if not _mot_dans_liste(mot, ASTRONYMES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des astronymes concernés par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    for cle in [mot, _supprimer_article(mot)]:
        if cle in LEXIQUE_ASTRONYMES:
            return LEXIQUE_ASTRONYMES[cle], f"Astronyme (lexicalisé) — forme attestée pour « {mot} »"
    for cle in [mot, _supprimer_article(mot)]:
        if "ال" + cle in LEXIQUE_ASTRONYMES:
            return LEXIQUE_ASTRONYMES["ال" + cle], f"Astronyme (lexicalisé) — forme attestée pour « {mot} »"

    return None, f"Astronyme : aucune forme documentée pour « {mot} »."


# -----------------------------------------------------------------------------
# Règles PRÉNOM — formes lexicalisées
# -----------------------------------------------------------------------------

def appliquer_regles_prenom(mot):
    """
    PRÉNOM : formes lexicalisées uniquement.
    Seuls les prénoms figurant dans PRENOMS_AVEC_DERIVATION sont traités.
    """
    mot = normaliser(mot).strip()

    if not _mot_dans_liste(mot, PRENOMS_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des prénoms concernés par les règles "
            f"de dérivation. Le mot est retourné sans modification."
        )

    if mot in LEXIQUE_PRENOMS:
        return LEXIQUE_PRENOMS[mot], f"Prénom (lexicalisé) — forme attestée pour « {mot} »"

    return None, f"Prénom : aucune forme documentée pour « {mot} »."


# -----------------------------------------------------------------------------
# Règles PENSÉE — religions, idéologies, courants philosophiques
# -----------------------------------------------------------------------------

def appliquer_regles_pensee(mot):
    """
    PENSÉE : dérivation par règle régulière (strip ال + ة si présente, puis ي).
    Seules les pensées figurant dans PENSEES_AVEC_DERIVATION sont traitées.
    """
    mot = normaliser(mot).strip()

    if not _mot_dans_liste(mot, PENSEES_AVEC_DERIVATION):
        return None, (
            f"« {mot} » n'est pas dans la liste des courants/religions concernés. "
            f"Le mot est retourné sans modification."
        )

    base = _supprimer_article(mot)
    # Règle T-1 : Terminaison ية → la nisba est déjà dans la base (ex. مسيحية → مسيحي)
    if base.endswith("ية"):
        racine = base[:-1]  # strip ة → conserve le ي final (c'est déjà la nisba)
        return {
            "singulier_masculin": racine,
            "singulier_feminin": racine + "ة",
            "pluriel_masculin_nominatif": racine + "ون",
            "pluriel_masculin_oblique": racine + "ين",
            "pluriel_feminin": racine + "ات",
        }, f"Règle T-1 — Terminaison ية : le mot contient déjà la nisba (ي conservé, ة supprimée) → « {racine} »"
    # Règle T-2 : Terminaison ة simple → supprimer ة puis ajouter ي
    if base.endswith("ة"):
        racine = base[:-1]
        return {
            "singulier_masculin": racine + "ي",
            "singulier_feminin": racine + "ية",
            "pluriel_masculin_nominatif": racine + "يون",
            "pluriel_masculin_oblique": racine + "يين",
            "pluriel_feminin": racine + "يات",
        }, f"Règle T-2 — Terminaison ة (ta marbuta) : suppression de ة + suffixes de Nisba sur « {racine} »"
    # Règle T-3 : Terminaison consonantique (ex. الإسلام → إسلامي)
    return {
        "singulier_masculin": base + "ي",
        "singulier_feminin": base + "ية",
        "pluriel_masculin_nominatif": base + "يون",
        "pluriel_masculin_oblique": base + "يين",
        "pluriel_feminin": base + "يات",
    }, f"Règle T-3 — Terminaison consonantique : suppression de ال (si présent) + suffixes de Nisba sur « {base} »"


# =============================================================================
# INSTANCES (الإعراب) — flexions visibles ou non
# =============================================================================

# Types pour lesquels les règles d'instances sont définies (selon regles_entites2_corrige).
# Tout type absent de cet ensemble n'a pas de règle d'instance retenue dans cette version.
TYPES_AVEC_INSTANCES = frozenset({
    "pays", "region", "supranational", "territoire", "ville",
    "patronyme", "prenom",
    "individuel", "collectif", "anthroponyme", "toponyme",
    "dynastie", "ethnonyme",
})
# Types 13 (pseudo_anthroponyme) et 14 (célébrité) : aucune règle d'instance
# spécifique retenue dans cette version (notebook regles_entites2_corrige §13/§14)


def appliquer_instances(mot, categorie):
    """
    Calcule les instances (flexions grammaticales) d'un nom propre.
    Retourne un dict (situation/description/formes) ou None si le type
    n'a pas de règle d'instance définie dans cette version.
    """
    if categorie not in TYPES_AVEC_INSTANCES:
        return None

    mot = normaliser(mot).strip()
    if not mot:
        return {"situation": 3, "description": "", "formes": None}

    base = _supprimer_article(mot)

    # ── Situation 2 → Règle I-2 : Pluriel masculin sain (dynasties, certains ethnonymes) ──
    if categorie in ("dynastie", "ethnonyme"):
        if base.endswith("ون"):
            racine = base[:-2]
            return {
                "situation": 2,
                "description": (
                    f"Règle I-2 — Alternance visible ✅ — Le mot « {base} » se termine par ون\n"
                    "→ Pluriel masculin sain (جمع مذكر سالم) détecté.\n"
                    "C'est le seul cas où l'écriture change visiblement en texte arabe "
                    "non voyellé : ون (nominatif) ↔ ين (accusatif/génitif)."
                ),
                "formes": {
                    "رفع (Nominatif / sujet)": base,
                    "نصب / جر (Accusatif-Génitif / complément)": racine + "ين",
                },
            }
        if base.endswith("ين"):
            racine = base[:-2]
            return {
                "situation": 2,
                "description": (
                    f"Règle I-2 — Alternance visible ✅ — Le mot « {base} » se termine par ين\n"
                    "→ Pluriel masculin sain (جمع مذكر سالم) détecté.\n"
                    "C'est le seul cas où l'écriture change visiblement en texte arabe "
                    "non voyellé : ون (nominatif) ↔ ين (accusatif/génitif)."
                ),
                "formes": {
                    "رفع (Nominatif / sujet)": racine + "ون",
                    "نصب / جر (Accusatif-Génitif / complément)": base,
                },
            }

    # ── Situation 1 → Règle I-1 : Se termine par ا ou ى → graphiquement stable ──────────
    if base.endswith("ا") or base.endswith("ى"):
        term = "ا" if base.endswith("ا") else "ى"
        return {
            "situation": 1,
            "description": (
                f"Règle I-1 — Graphiquement stable ✅ — Le mot « {mot} » se termine par {term}\n"
                "→ En écriture arabe non voyellée, cette terminaison rend le nom propre "
                "invariable graphiquement dans tous les cas grammaticaux."
            ),
            "formes": {
                "رفع — Nominatif (sujet) مرفوع": mot,
                "نصب — Accusatif (complément) منصوب": mot,
                "جر — Génitif (préposition) مجرور": mot,
            },
        }

    # ── Situation 3 : Tous les autres ────────────────────────────────────────
    # Pour les mots arabes connus (dans les listes), on montre les voyelles
    # casuelles théoriques car ces mots ont une déclinaison arabe connue.
    # Pour les mots étrangers/non recensés, pas de voyelles ajoutées (le mot
    # reste tel quel car il ne prend pas la déclinaison arabe standard).
    _toutes_listes = (
        PAYS_AVEC_DERIVATION
        | VILLES_AVEC_DERIVATION
        | SUPRANATIONAL_AVEC_DERIVATION
        | REGIONS_AVEC_DERIVATION
        | DYNASTIES_AVEC_DERIVATION
        | ETHNONYMES_AVEC_DERIVATION
        | PRENOMS_AVEC_DERIVATION
    )
    if _mot_dans_liste(mot, _toutes_listes):
        # Mot arabe connu → voyelles casuelles théoriques
        return {
            "situation": 3,
            "description": (
                f"Règle I-1 — Déclinaison arabe connue\n"
                f"Le mot « {mot} » est recensé dans la base → déclinaison arabe standard.\n"
                "En texte non voyellé, les trois formes sont graphiquement identiques "
                "(la différence se marque uniquement par la voyelle finale)."
            ),
            "formes": {
                "رفع — Nominatif (sujet) مرفوع": mot + "\u064f",
                "نصب — Accusatif (complément) منصوب": mot + "\u064e",
                "جر — Génitif (préposition) مجرور": mot + "\u0650",
            },
        }
    # Mot étranger ou non recensé → pas de voyelles ajoutées, le mot reste tel quel
    return {
        "situation": 3,
        "description": (
            f"Règle I-1 — Mot non recensé — forme inchangée\n"
            f"Le mot « {mot} » n'est pas recensé dans la base → traité comme mot étranger.\n"
            "Ce nom propre ne prend pas de voyelles casuelles arabes. "
            "La forme reste identique dans tous les cas."
        ),
        "formes": {
            "رفع — Nominatif (sujet) مرفوع": mot,
            "نصب — Accusatif (complément) منصوب": mot,
            "جر — Génitif (préposition) مجرور": mot,
        },
    }


# =============================================================================
# FONCTION PRINCIPALE D'APPLICATION DES RÈGLES
# =============================================================================

def appliquer_regles(mot, categorie):
    """
    Point d'entrée principal pour les dérivés (Nisba / النسبة).
    Retourne (resultats_dict, explication_str).
    """
    mot = normaliser(mot).strip()
    if not mot:
        return _resultat_vide(), "Aucun mot saisi"

    if categorie == "pays":
        return appliquer_regles_pays(mot)

    if categorie == "region":
        return appliquer_regles_region(mot)

    if categorie == "supranational":
        return appliquer_regles_supranational(mot)

    if categorie == "ville":
        return appliquer_regles_ville(mot)

    if categorie == "ethnonyme":
        return appliquer_regles_ethnonyme(mot)

    if categorie == "dynastie":
        return appliquer_regles_dynastie(mot)

    if categorie == "geonyme":
        return appliquer_regles_geonyme(mot)

    if categorie == "astronyme":
        return appliquer_regles_astronyme(mot)

    if categorie == "prenom":
        return appliquer_regles_prenom(mot)

    if categorie == "pensee":
        return appliquer_regles_pensee(mot)

    # Toutes les autres catégories : pas de dérivation dans cette version
    cat_info = CATEGORIES.get(categorie, {})
    nom_fr = cat_info.get("nom_fr", categorie)
    return None, (
        f"{nom_fr} : aucune règle productive générale de dérivation n'est retenue "
        f"dans cette version. Les dérivés éventuellement attestés seront traités "
        f"ultérieurement comme formes lexicalisées."
    )


# =============================================================================
# LABELS D'AFFICHAGE
# =============================================================================

LABELS_FORMES = {
    "singulier_masculin": ("مذكر مفرد", "Singulier masculin"),
    "singulier_feminin": ("مؤنث مفرد", "Singulier féminin"),
    "pluriel_masculin_nominatif": ("جمع مذكر مرفوع", "Pluriel masc. nominatif"),
    "pluriel_masculin_oblique": ("جمع مذكر منصوب/مجرور", "Pluriel masc. oblique"),
    "pluriel_feminin": ("جمع مؤنث", "Pluriel féminin"),
}


# Correspondance statut → badge pour l'affichage
STATUT_LABELS = {
    "semi-productive": ("⚙️", "Semi-productive", "Règles générales + lexique d'exceptions"),
    "productive": ("✅", "Productive", "Règle automatique applicable à toute la classe"),
    "lexicalisée": ("📖", "Lexicalisée", "Forme attestée stockée dans un lexique"),
    "non retenu v1": ("⏳", "Non retenu v1", "Traitement différé à une version ultérieure"),
}
