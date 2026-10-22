-- Nara : manipulation des ombres - code partage (serveur + client)

NARA = NARA or {}
NARA.Casts = NARA.Casts or {}   -- [joueur] = technique en cours (serveur : etat, client : copie + rendu)

local C = NARA.Config

CreateConVar("nara_kage_damage_scale", "1", bit.bor(FCVAR_ARCHIVE, FCVAR_NOTIFY, FCVAR_REPLICATED),
	"Nara : multiplicateur des degats (Kubishibari, Kage Nui)")
CreateConVar("nara_kage_affect_players", "1", bit.bor(FCVAR_ARCHIVE, FCVAR_NOTIFY, FCVAR_REPLICATED),
	"Nara : les ombres peuvent attraper les joueurs (1) ou seulement les PNJ (0)")

-- ---------------------------------------------------------------- sol

local function IgnoreLiving(e)
	return not (e:IsPlayer() or e:IsNPC() or e:IsNextBot() or e:IsWeapon())
end

-- Point du sol sous pos (ou nil s'il n'y a rien dans les 'down' unites)
function NARA.Ground(pos, up, down)
	local tr = util.TraceLine({
		start = pos + Vector(0, 0, up or 30),
		endpos = pos - Vector(0, 0, down or 90),
		mask = MASK_SOLID,
		filter = IgnoreLiving,
	})
	if not tr.Hit or tr.StartSolid or tr.HitNormal.z < 0.55 then return nil end
	return tr.HitPos, tr.HitNormal
end

-- Ligne au sol entre deux points, un point toutes les 'step' unites
function NARA.GroundLine(a, b, step)
	step = step or 12
	local pts = {}
	local d = b - a
	d.z = 0
	local len = d:Length()
	local n = math.max(1, math.ceil(len / step))
	local last = a
	for i = 0, n do
		local p = a + (b - a) * (i / n)
		local g = NARA.Ground(Vector(p.x, p.y, math.max(p.z, last.z)), 40, 140)
		if g then last = g end
		pts[#pts + 1] = g or Vector(p.x, p.y, last.z)
	end
	return pts
end

function NARA.PathLength(pts, upto)
	local L = 0
	for i = 2, upto or #pts do L = L + pts[i]:Distance(pts[i - 1]) end
	return L
end

-- Echantillonne une ligne brisee en n points regulierement espaces
function NARA.Resample(pts, n)
	local out = {}
	if #pts == 0 then return out end
	if #pts == 1 then
		for i = 1, n do out[i] = pts[1] end
		return out
	end
	local total = NARA.PathLength(pts)
	local seg, acc = 2, 0
	for i = 1, n do
		local want = total * (i - 1) / math.max(1, n - 1)
		while seg < #pts and acc + pts[seg]:Distance(pts[seg - 1]) < want do
			acc = acc + pts[seg]:Distance(pts[seg - 1])
			seg = seg + 1
		end
		local l = pts[seg]:Distance(pts[seg - 1])
		local t = l > 0 and math.Clamp((want - acc) / l, 0, 1) or 0
		out[i] = LerpVector(t, pts[seg - 1], pts[seg])
	end
	return out
end

-- ---------------------------------------------------------------- cibles

function NARA.IsTarget(ent, caster)
	if not IsValid(ent) or ent == caster then return false end
	if ent:IsPlayer() then
		return ent:Alive() and GetConVar("nara_kage_affect_players"):GetBool()
	end
	if ent:IsNPC() or ent:IsNextBot() then
		return C.AffectNPCs and (ent:Health() > 0 or ent:IsNextBot())
	end
	return false
end

-- Hauteur du cou d'une cible (pour l'etreinte)
function NARA.NeckPos(ent)
	local b = ent:LookupBone("ValveBiped.Bip01_Neck1") or ent:LookupBone("ValveBiped.Bip01_Head1")
	if b then
		local p = ent:GetBonePosition(b)
		if p and p ~= ent:GetPos() then return p end
	end
	local mins, maxs = ent:OBBMins(), ent:OBBMaxs()
	return ent:GetPos() + Vector(0, 0, (maxs.z - mins.z) * 0.82)
end

-- ---------------------------------------------------------------- etats

function NARA.CasterFrozen(rec)
	local p = rec.phase
	return p == NARA.PH_WINDUP or p == NARA.PH_STEER or p == NARA.PH_TRAVEL
		or p == NARA.PH_CHOKE or p == NARA.PH_PIERCE
end

function NARA.WantKneel(rec)
	local p = rec.phase
	if rec.tech == 1 then return p == NARA.PH_WINDUP or p == NARA.PH_STEER end
	if rec.tech == 2 then return p == NARA.PH_TRAVEL or p == NARA.PH_CHOKE end
	return false
end

function NARA.WantArms(rec)
	local p = rec.phase
	return p == NARA.PH_WINDUP or p == NARA.PH_STEER or p == NARA.PH_TRAVEL or p == NARA.PH_BOUND
		or p == NARA.PH_CHOKE or p == NARA.PH_PIERCE
end

-- ---------------------------------------------------------------- commandes
-- Le lanceur est immobile pendant le sceau ; la cible prise imite ses mouvements.

local MIMIC_KEYS = bit.bor(IN_JUMP, IN_DUCK, IN_SPEED, IN_WALK)

hook.Add("StartCommand", "NaraKage_Cmd", function(ply, cmd)
	local rec = NARA.Casts[ply]
	if rec and NARA.CasterFrozen(rec) then
		if SERVER then
			rec.keyFwd = cmd:KeyDown(IN_FORWARD)
			rec.keyBack = cmd:KeyDown(IN_BACK)
		end
		cmd:ClearMovement()
		cmd:RemoveKey(IN_JUMP)
		cmd:RemoveKey(IN_DUCK)
		cmd:RemoveKey(IN_SPEED)
	end

	-- le lanceur transmet ses mouvements a sa cible
	if SERVER and rec and rec.phase == NARA.PH_BOUND and IsValid(rec.target) and rec.target:IsPlayer() then
		local t = rec.target
		t:SetNW2Float("NaraMF", cmd:GetForwardMove())
		t:SetNW2Float("NaraMS", cmd:GetSideMove())
		t:SetNW2Int("NaraMB", bit.band(cmd:GetButtons(), MIMIC_KEYS))
		t:SetNW2Float("NaraMY", (rec.targetYaw or 0) + math.AngleDifference(cmd:GetViewAngles().y, rec.casterYaw or 0))
	end

	local by = ply:GetNW2Entity("NaraBy")
	if IsValid(by) then
		cmd:ClearMovement()
		cmd:ClearButtons()
		if ply:GetNW2Int("NaraMode") == 1 then
			cmd:SetForwardMove(ply:GetNW2Float("NaraMF"))
			cmd:SetSideMove(ply:GetNW2Float("NaraMS"))
			cmd:SetButtons(ply:GetNW2Int("NaraMB"))
			local a = cmd:GetViewAngles()
			a.y = ply:GetNW2Float("NaraMY")
			cmd:SetViewAngles(a)
		end
	end
end)
