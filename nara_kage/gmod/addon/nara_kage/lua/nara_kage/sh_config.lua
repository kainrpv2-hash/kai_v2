-- Nara : manipulation des ombres - reglages
-- Toutes les distances sont en unites Source (1 u = 1 pouce ; un joueur fait 72 u).

NARA = NARA or {}

NARA.Config = {
	-- ------------------------------------------------------------ Kagemane no Jutsu
	-- Le lanceur met un genou a terre et forme le sceau, puis la camera passe
	-- dans la pointe de l'ombre et le joueur la dirige a la souris.
	WindupTime     = 1.15,  -- genou a terre + sceau avant que l'ombre parte (s)
	CamDiveTime    = 0.45,  -- plongee de la camera vers la pointe de l'ombre (s)
	SteerTime      = 13,    -- compteur affiche en bas de l'ecran (s)
	ShadowSpeed    = 250,   -- vitesse de la pointe (u/s)
	BoostSpeed     = 430,   -- en maintenant Avancer (Z / W)
	SlowSpeed      = 90,    -- en maintenant Reculer (S)
	TurnRate       = 170,   -- vitesse de virage max de l'ombre (degres/s)
	MaxLength      = 3000,  -- longueur max de l'ombre (u)
	CatchRadius    = 26,    -- l'ombre attrape ce qui est a cette distance de sa pointe
	PossessTime    = 10,    -- duree de la possession une fois la cible prise (s)
	BreakDistance  = 3400,  -- le lien casse si le lanceur s'eloigne plus que ca
	KneelLeg       = "R",   -- genou pose au sol : "R" (droit) ou "L" (gauche)

	-- Camera dans la pointe de l'ombre
	CamHeight      = 11,    -- hauteur de l'oeil au-dessus du sol
	CamBack        = 6,     -- recul derriere la pointe (on voit le bout de la tete de l'ombre)
	CamFOV         = 100,
	CamPitchMin    = -55,
	CamPitchMax    = 35,

	-- ------------------------------------------------------------ Kage Kubishibari no Jutsu
	ChokeRange     = 1100,  -- portee si la cible n'est pas deja prise dans l'ombre
	ChokeTendrils  = 5,     -- nombre de mains d'ombre
	ChokeClimbTime = 1.3,   -- temps pour que les mains montent jusqu'au cou (s)
	ChokeTime      = 6,     -- duree de l'etranglement (s)
	ChokeDPS       = 9,     -- degats par seconde une fois les mains au cou

	-- ------------------------------------------------------------ Kage Nui no Jutsu
	NuiRange       = 1300,
	NuiNeedles     = 11,    -- nombre d'aiguilles d'ombre
	NuiDamage      = 40,    -- degats a l'impact (partages entre les aiguilles)
	NuiHoldTime    = 1.6,   -- la cible reste clouee (s)

	-- ------------------------------------------------------------ commun
	TravelSpeed    = 1100,  -- vitesse de l'ombre envoyee directement sur une cible (u/s)
	RetractSpeed   = 1800,  -- vitesse de retour de l'ombre (u/s)
	Width          = 15,    -- largeur de la bande d'ombre
	PoolRadius     = 34,    -- rayon de l'ombre sous le lanceur
	TargetPool     = 30,    -- rayon de l'ombre sous la cible
	Cooldown       = 4,     -- delai entre deux techniques (s)
	AffectNPCs     = true,
	ScreenFX       = true,  -- ecran desature + bords d'encre en vue ombre

	-- Sons (chemins relatifs a sound/). Mets "" pour couper un son.
	Sounds = {
		Mudra   = "nara_kage/mudra.wav",
		Cast    = "nara_kage/cast.wav",
		Crawl   = "nara_kage/crawl_loop.wav",
		Bind    = "nara_kage/bind.wav",
		Choke   = "nara_kage/choke.wav",
		Pierce  = "nara_kage/pierce.wav",
		Release = "nara_kage/release.wav",
		Tick    = "nara_kage/tick.wav",
	},
}

-- Ordre des techniques dans l'arme (touche R pour changer)
NARA.Techniques = {
	{ id = "kagemane",    name = "Kagemane no Jutsu",        jp = "影真似の術",   fr = "Manipulation des ombres" },
	{ id = "kubishibari", name = "Kage Kubishibari no Jutsu", jp = "影首縛りの術", fr = "Etreinte de l'ombre" },
	{ id = "kagenui",     name = "Kage Nui no Jutsu",        jp = "影縫いの術",   fr = "Couture des ombres" },
}

-- Phases reseau d'une technique
NARA.PH_NONE    = 0
NARA.PH_WINDUP  = 1   -- genou a terre + sceau
NARA.PH_STEER   = 2   -- l'ombre avance, dirigee depuis sa pointe (compteur 13 s)
NARA.PH_TRAVEL  = 3   -- l'ombre file droit vers une cible (Kubishibari / Kage Nui)
NARA.PH_BOUND   = 4   -- cible prise : elle imite le lanceur
NARA.PH_CHOKE   = 5   -- mains d'ombre au cou
NARA.PH_PIERCE  = 6   -- aiguilles d'ombre
NARA.PH_RETRACT = 7   -- l'ombre revient au lanceur
