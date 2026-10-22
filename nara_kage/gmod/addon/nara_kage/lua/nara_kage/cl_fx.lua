-- Nara : Kagemane no Jutsu - reception reseau et rendu de l'ombre
-- Style de la video de reference : bande noire pleine aux courbes lisses, bord doux,
-- largeur qui respire a peine, pointe effilee qui serpente au sol. Pas de fumee.

NARA = NARA or {}
local C = NARA.Config
local Casts = NARA.Casts

local MAT_RIBBON = Material("nara_kage/shadow_ribbon")
local MAT_POOL = Material("nara_kage/shadow_pool")
local UP = Vector(0, 0, 1)

local function ease(x) x = math.Clamp(x, 0, 1) return x * x * (3 - 2 * x) end
local function easeOut(x) x = math.Clamp(x, 0, 1) return 1 - (1 - x) ^ 3 end

-- ---------------------------------------------------------------- reseau

net.Receive("nara_kage_state", function()
	local ply = net.ReadEntity()
	local phase = net.ReadUInt(3)
	local t0 = net.ReadFloat()
	local target = net.ReadEntity()
	local yaw = net.ReadFloat()
	local reset = net.ReadBool()
	if not IsValid(ply) then return end

	local rec = Casts[ply]
	if not rec or reset then
		rec = { path = {}, wKneel = rec and rec.wKneel or 0, wArms = rec and rec.wArms or 0 }
		Casts[ply] = rec
	end
	local prev = rec.phase
	rec.phase, rec.phaseStart, rec.lockYaw = phase, t0, yaw
	rec.target = IsValid(target) and target or rec.target
	rec.localStart = CurTime()
	if prev ~= phase then
		-- ce qui est affiche au moment du changement sert de depart aux transitions
		rec.morphFrom = rec.drawPts
		if phase == NARA.PH_RETRACT then rec.retractPts = rec.drawPts end
		if phase == NARA.PH_BOUND then rec.catchStart = CurTime() end
	end
	NARA.EnsurePoseCallback(ply)
	if IsValid(rec.target) then NARA.EnsurePoseCallback(rec.target) end
end)

net.Receive("nara_kage_pts", function()
	local ply = net.ReadEntity()
	local first = net.ReadUInt(12)
	local n = net.ReadUInt(7)
	local pts = {}
	for i = 1, n do pts[i] = net.ReadVector() end
	if not IsValid(ply) then return end
	local rec = Casts[ply]
	if not rec then
		rec = { path = {}, wKneel = 0, wArms = 0, phase = NARA.PH_NONE, phaseStart = CurTime(), localStart = CurTime() }
		Casts[ply] = rec
	end
	for i = 1, n do rec.path[first + i - 1] = pts[i] end
end)

-- ---------------------------------------------------------------- trace de l'ombre

local function Feet(ent)
	return NARA.Ground(ent:GetPos(), 12, 48) or ent:GetPos()
end

-- Lien au sol lanceur -> cible, recalcule 10 fois par seconde
local function LinkLine(rec, ply)
	if not IsValid(rec.target) then return rec.linkPts end
	if not rec.linkPts or CurTime() > (rec.linkNext or 0) then
		rec.linkNext = CurTime() + 0.1
		rec.linkPts = NARA.GroundLine(Feet(ply), Feet(rec.target), 14)
	end
	return rec.linkPts
end

local function Truncate(pts, len)
	local out = { pts[1] }
	local acc = 0
	for i = 2, #pts do
		local l = pts[i]:Distance(pts[i - 1])
		if acc + l >= len then
			out[#out + 1] = LerpVector(l > 0 and (len - acc) / l or 0, pts[i - 1], pts[i])
			return out
		end
		acc = acc + l
		out[#out + 1] = pts[i]
	end
	return out
end

-- Ligne d'ombre a dessiner pour cette frame
local function CurrentLine(ply, rec)
	local p = rec.phase
	local now = CurTime()
	if p == NARA.PH_STEER then
		local path = rec.path
		if #path == 0 then return nil end
		-- la pointe affichee suit le dernier point recu en douceur
		local last = path[#path]
		rec.tipDisp = rec.tipDisp and LerpVector(math.min(1, FrameTime() * 14), rec.tipDisp, last) or last
		local pts = {}
		for i = 1, #path - 1 do pts[i] = path[i] end
		pts[#pts + 1] = rec.tipDisp
		return pts
	elseif p == NARA.PH_BOUND then
		local link = LinkLine(rec, ply)
		if not link then return rec.drawPts end
		-- le trace courbe de la poursuite se tend en ligne droite vers la cible
		local k = rec.morphFrom and ease((now - (rec.catchStart or 0)) / 0.55) or 1
		if k >= 1 or not rec.morphFrom or #rec.morphFrom < 2 then return link end
		local n = math.max(#link, 24)
		local a = NARA.Resample(rec.morphFrom, n)
		local b = NARA.Resample(link, n)
		local out = {}
		for i = 1, n do out[i] = LerpVector(k, a[i], b[i]) end
		return out
	elseif p == NARA.PH_RETRACT then
		-- le lanceur ravale son ombre : elle se retire depuis la pointe
		local src = rec.retractPts
		if not src or #src < 2 then return nil end
		rec.retractLen = rec.retractLen or NARA.PathLength(src)
		local left = rec.retractLen - C.RetractSpeed * (now - rec.localStart)
		if left <= 2 then return nil end
		local src2 = { Feet(ply) }
		for i = 2, #src do src2[i] = src[i] end
		return Truncate(src2, left)
	end
	return nil
end

-- ---------------------------------------------------------------- dessin

-- Flaque elliptique a plat sur le sol
local function Pool(center, yaw, halfLen, halfWid, alpha)
	if halfLen < 0.5 or alpha <= 0 then return end
	local F = Angle(0, yaw, 0):Forward() * halfLen
	local S = F:Cross(UP):GetNormalized() * halfWid
	local c = center + UP * 0.6
	local col = C.Color
	render.SetMaterial(MAT_POOL)
	mesh.Begin(MATERIAL_QUADS, 1)
	mesh.Position(c - F - S) mesh.TexCoord(0, 0, 0) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
	mesh.Position(c + F - S) mesh.TexCoord(0, 1, 0) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
	mesh.Position(c + F + S) mesh.TexCoord(0, 1, 1) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
	mesh.Position(c - F + S) mesh.TexCoord(0, 0, 1) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
	mesh.End()
end

-- Courbe lisse (Catmull-Rom) passant par les points, un point toutes les ~3 u :
-- plus aucune cassure dans les virages
local function Smooth(pts)
	local n = #pts
	if n < 3 then return pts end
	local out = {}
	for i = 1, n - 1 do
		local p0, p1, p2, p3 = pts[math.max(1, i - 1)], pts[i], pts[i + 1], pts[math.min(n, i + 2)]
		local steps = math.max(1, math.ceil(p1:Distance(p2) / 3))
		for k = 0, steps - 1 do
			local t = k / steps
			local t2, t3 = t * t, t * t * t
			out[#out + 1] = (p1 * 2 + (p2 - p0) * t + (p0 * 2 - p1 * 5 + p2 * 4 - p3) * t2 + (p1 * 3 - p0 - p2 * 3 + p3) * t3) * 0.5
			if #out >= 4000 then return out end
		end
	end
	out[#out + 1] = pts[n]
	return out
end

-- Bande d'ombre : largeur qui respire doucement, depart evase dans la flaque, pointe en aiguille
local function DrawRibbon(raw, width, alpha)
	local pts = Smooth(raw)
	local n = #pts
	if n < 2 then return end
	local s = { 0 }
	for i = 2, n do s[i] = s[i - 1] + pts[i]:Distance(pts[i - 1]) end
	local total = s[n]
	if total < 1 then return end
	local tipLen = math.min(C.TipLength, total * 0.6)
	local col = C.Color

	local L, R = {}, {}
	for i = 1, n do
		local a = pts[math.max(1, i - 1)]
		local b = pts[math.min(n, i + 1)]
		local dir = b - a
		dir.z = 0
		if dir:LengthSqr() < 1e-4 then dir = Vector(1, 0, 0) end
		dir:Normalize()
		local side = dir:Cross(UP)
		local si = s[i]
		-- variation lente, fixee au sol (elle ne scintille pas quand l'ombre avance)
		local w = width * (1 + C.WidthBreath * (0.6 * math.sin(si * 0.021 + 1.3) + 0.4 * math.sin(si * 0.057 + 0.4)))
		w = w * (math.Clamp((total - si) / tipLen, 0, 1) ^ 0.6)   -- pointe en aiguille
		w = w * (1 + 0.6 * (1 - math.Clamp(si / 30, 0, 1)))      -- s'evase en sortant de la flaque
		local c = pts[i] + UP * 0.7
		L[i], R[i] = c - side * w, c + side * w
	end

	render.SetMaterial(MAT_RIBBON)
	mesh.Begin(MATERIAL_QUADS, n - 1)
	for i = 1, n - 1 do
		local u1, u2 = s[i] / 160, s[i + 1] / 160
		mesh.Position(L[i]) mesh.TexCoord(0, u1, 0) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
		mesh.Position(L[i + 1]) mesh.TexCoord(0, u2, 0) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
		mesh.Position(R[i + 1]) mesh.TexCoord(0, u2, 1) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
		mesh.Position(R[i]) mesh.TexCoord(0, u1, 1) mesh.Color(col.r, col.g, col.b, alpha) mesh.AdvanceVertex()
	end
	mesh.End()
end

-- ---------------------------------------------------------------- mise a jour + rendu

hook.Add("Think", "NaraKage_ClientThink", function()
	local dt = FrameTime()
	for ply, rec in pairs(Casts) do
		if not IsValid(ply) then
			Casts[ply] = nil
		else
			rec.wKneel = Lerp(math.min(1, dt * 7), rec.wKneel or 0, NARA.WantKneel(rec) and 1 or 0)
			rec.wArms = Lerp(math.min(1, dt * 9), rec.wArms or 0, NARA.WantArms(rec) and 1 or 0)
			if rec.phase == NARA.PH_NONE and rec.wKneel < 0.01 and rec.wArms < 0.01 then Casts[ply] = nil end
		end
	end
end)

-- opacite de la flaque du lanceur selon la phase
local function PoolAlpha(rec, now)
	local el = now - (rec.localStart or now)
	if rec.phase == NARA.PH_WINDUP then return ease(el / 0.4) end
	if rec.phase == NARA.PH_NONE then return 1 - ease(el / 0.3) end
	if rec.phase == NARA.PH_RETRACT then
		return 1 - ease((el - (rec.retractLen or 0) / C.RetractSpeed) / 0.3)
	end
	return 1
end

hook.Add("PostDrawTranslucentRenderables", "NaraKage_Draw", function(depth, sky)
	if depth or sky then return end
	local now = CurTime()
	for ply, rec in pairs(Casts) do
		if IsValid(ply) then
			-- l'ombre du lanceur s'etale devant lui
			local pa = PoolAlpha(rec, now)
			if pa > 0.01 then
				local grow = rec.phase == NARA.PH_WINDUP and easeOut((now - rec.localStart) / 0.6) or 1
				local yaw = rec.lockYaw or ply:GetAngles().y
				local center = Feet(ply) + Angle(0, yaw, 0):Forward() * C.PoolForward * grow
				Pool(center, yaw, C.PoolLength * grow, C.PoolWidth * grow, 250 * pa)
			end

			local line = CurrentLine(ply, rec)
			rec.drawPts = rec.phase ~= NARA.PH_NONE and (line or rec.drawPts) or nil
			if line then DrawRibbon(line, C.Width, 252) end

			-- l'ombre de la cible prise se fond dans celle du lanceur
			if rec.phase == NARA.PH_BOUND and IsValid(rec.target) then
				local k = easeOut((now - (rec.catchStart or now)) / 0.35)
				Pool(Feet(rec.target), 0, C.TargetPool * k, C.TargetPool * k, 245)
			end
		end
	end
end)
