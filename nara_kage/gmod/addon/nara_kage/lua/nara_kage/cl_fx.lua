-- Nara : manipulation des ombres - reception reseau et rendu des ombres

NARA = NARA or {}
local C = NARA.Config
local Casts = NARA.Casts

local MAT = {
	ribbon = Material("nara_kage/shadow_ribbon"),
	pool   = Material("nara_kage/shadow_pool"),
	ring   = Material("nara_kage/shadow_ring"),
	strand = Material("nara_kage/shadow_strand"),
	needle = Material("nara_kage/shadow_needle"),
	hand   = Material("nara_kage/shadow_hand"),
}
NARA.MAT = MAT
local WISP = "nara_kage/shadow_wisp"

local INK = Color(0, 0, 0)
local UP = Vector(0, 0, 1)

local function ease(x) x = math.Clamp(x, 0, 1) return x * x * (3 - 2 * x) end
local function easeOut(x) x = math.Clamp(x, 0, 1) return 1 - (1 - x) ^ 3 end

-- ---------------------------------------------------------------- reseau

net.Receive("nara_kage_state", function()
	local ply = net.ReadEntity()
	local phase = net.ReadUInt(4)
	local tech = net.ReadUInt(3)
	local t0 = net.ReadFloat()
	local target = net.ReadEntity()
	local yaw = net.ReadFloat()
	local reset = net.ReadBool()
	if not IsValid(ply) then return end

	local rec = Casts[ply]
	if not rec or reset then
		local old = rec
		rec = { path = {}, wKneel = old and old.wKneel or 0, wArms = old and old.wArms or 0, seed = math.random(1, 9999) }
		Casts[ply] = rec
	end
	local prev = rec.phase
	rec.phase, rec.tech, rec.phaseStart, rec.lockYaw = phase, tech, t0, yaw
	rec.target = IsValid(target) and target or rec.target
	rec.localStart = CurTime()

	-- ce qui est affiche au moment du changement sert de point de depart aux transitions
	if prev ~= phase then
		rec.morphFrom = rec.drawPts
		rec.morphStart = CurTime()
		if phase == NARA.PH_RETRACT then rec.retractPts = rec.drawPts end
		if phase == NARA.PH_WINDUP or phase == NARA.PH_TRAVEL then
			rec.ringStart = CurTime()
			rec.burst = "start"
		elseif phase == NARA.PH_BOUND or phase == NARA.PH_CHOKE or phase == NARA.PH_PIERCE then
			rec.burst = "catch"
			rec.catchStart = CurTime()
			rec.needles = nil
		end
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
		rec = { path = {}, wKneel = 0, wArms = 0, seed = math.random(1, 9999), phase = NARA.PH_NONE, tech = 1,
			phaseStart = CurTime() }
		Casts[ply] = rec
	end
	for i = 1, n do rec.path[first + i - 1] = pts[i] end
end)

-- ---------------------------------------------------------------- geometrie de l'ombre

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

-- Pointe affichee : suit le dernier point recu en douceur
local function TipLine(rec)
	local path = rec.path
	if #path == 0 then return nil end
	local last = path[#path]
	rec.tipDisp = rec.tipDisp and LerpVector(math.min(1, FrameTime() * 14), rec.tipDisp, last) or last
	local pts = {}
	for i = 1, #path do pts[i] = path[i] end
	-- la pointe interpolee remplace le dernier point
	if #pts >= 2 then pts[#pts] = rec.tipDisp end
	return pts
end

local function Truncate(pts, len)
	if not pts or #pts < 2 then return pts end
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

-- Calcule la ligne d'ombre a dessiner pour cette frame
local function CurrentLine(ply, rec)
	local p = rec.phase
	local now = CurTime()
	if p == NARA.PH_STEER or p == NARA.PH_TRAVEL then
		return TipLine(rec)
	elseif p == NARA.PH_BOUND or p == NARA.PH_CHOKE or p == NARA.PH_PIERCE then
		local link = LinkLine(rec, ply)
		if not link then return rec.drawPts end
		-- le trace courbe de la poursuite se tend en ligne droite vers la cible
		local k = rec.morphFrom and ease((now - (rec.morphStart or 0)) / 0.55) or 1
		if k >= 1 or not rec.morphFrom or #rec.morphFrom < 2 then return link end
		local n = math.max(#link, 24)
		local a = NARA.Resample(rec.morphFrom, n)
		local b = NARA.Resample(link, n)
		local out = {}
		for i = 1, n do out[i] = LerpVector(k, a[i], b[i]) end
		return out
	elseif p == NARA.PH_RETRACT then
		local src = rec.retractPts
		if not src or #src < 2 then return nil end
		rec.retractLen = rec.retractLen or NARA.PathLength(src)
		local left = rec.retractLen - C.RetractSpeed * (now - rec.localStart)
		if left <= 2 then return nil end
		-- le lanceur ravale son ombre : elle se retire depuis la pointe
		local src2 = { Feet(ply) }
		for i = 2, #src do src2[i] = src[i] end
		return Truncate(src2, left)
	end
	return nil
end

-- ---------------------------------------------------------------- dessin

local function GroundQuad(mat, center, radius, rot, col, normal)
	render.SetMaterial(mat)
	render.DrawQuadEasy(center + (normal or UP) * 0.6, normal or UP, radius * 2, radius * 2, col, rot)
end

-- Bande d'ombre au sol : largeur qui ondule, pointe arrondie qui tatonne
local function DrawRibbon(pts, width, alpha, t, moving, seed)
	if not pts or #pts < 2 then return end
	local n = #pts
	-- abscisses curvilignes
	local s = { 0 }
	for i = 2, n do s[i] = s[i - 1] + pts[i]:Distance(pts[i - 1]) end
	local total = s[n]
	if total < 1 then return end
	local headLen = math.min(46, total * 0.5)

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
		local toTip = total - si
		local w = width
		w = w * (1 + 0.10 * math.sin(si * 0.09 - t * 5.5 + seed) + 0.06 * math.sin(si * 0.23 + t * 8.3))
		w = w * math.sqrt(math.Clamp(toTip / headLen, 0, 1))         -- tete arrondie
		w = w * (1 + 0.35 * (1 - math.Clamp(si / 40, 0, 1)))          -- s'evase en sortant de la flaque
		local off = Vector(0, 0, 0)
		if moving then
			local tipK = 1 - math.Clamp(toTip / 110, 0, 1)
			off = side * math.sin(t * 11 + si * 0.15 + seed) * 2.6 * tipK
		end
		local c = pts[i] + UP * 0.7 + off
		L[i], R[i] = c - side * w, c + side * w
	end

	render.SetMaterial(MAT.ribbon)
	mesh.Begin(MATERIAL_QUADS, n - 1)
	for i = 1, n - 1 do
		local u1 = s[i] / 90 - t * 0.35
		local u2 = s[i + 1] / 90 - t * 0.35
		mesh.Position(L[i]) mesh.TexCoord(0, u1, 0) mesh.Color(0, 0, 0, alpha) mesh.AdvanceVertex()
		mesh.Position(L[i + 1]) mesh.TexCoord(0, u2, 0) mesh.Color(0, 0, 0, alpha) mesh.AdvanceVertex()
		mesh.Position(R[i + 1]) mesh.TexCoord(0, u2, 1) mesh.Color(0, 0, 0, alpha) mesh.AdvanceVertex()
		mesh.Position(R[i]) mesh.TexCoord(0, u1, 1) mesh.Color(0, 0, 0, alpha) mesh.AdvanceVertex()
	end
	mesh.End()
	return total
end

-- Petites antennes d'ombre qui tatonnent devant la pointe (bandes a plat sur le sol)
local function DrawFeelers(pts, t, seed)
	if not pts or #pts < 3 then return end
	local tip = pts[#pts]
	local dir = tip - pts[math.max(1, #pts - 3)]
	dir.z = 0
	if dir:LengthSqr() < 1e-3 then return end
	dir:Normalize()
	local side = dir:Cross(UP)
	render.SetMaterial(MAT.strand)
	for k = -1, 1, 2 do
		local P, W = {}, {}
		for j = 0, 5 do
			local f = j / 5
			local sway = math.sin(t * 9 + k * 1.7 + f * 3 + seed) * 4 * f
			P[j + 1] = tip - dir * 8 + dir * (f * 16) + side * (k * (2.5 + 5 * f) + sway) + UP * 0.9
			W[j + 1] = 2.2 * (1 - f) + 0.2
		end
		mesh.Begin(MATERIAL_QUADS, 5)
		for j = 1, 5 do
			local a, b = P[j], P[j + 1]
			local d = b - a
			d.z = 0
			d:Normalize()
			local sd = d:Cross(UP)
			local v1, v2 = (j - 1) / 5 * 2, j / 5 * 2
			mesh.Position(a - sd * W[j]) mesh.TexCoord(0, 0, v1) mesh.Color(0, 0, 0, 235) mesh.AdvanceVertex()
			mesh.Position(b - sd * W[j + 1]) mesh.TexCoord(0, 0, v2) mesh.Color(0, 0, 0, 235) mesh.AdvanceVertex()
			mesh.Position(b + sd * W[j + 1]) mesh.TexCoord(0, 1, v2) mesh.Color(0, 0, 0, 235) mesh.AdvanceVertex()
			mesh.Position(a + sd * W[j]) mesh.TexCoord(0, 1, v1) mesh.Color(0, 0, 0, 235) mesh.AdvanceVertex()
		end
		mesh.End()
	end
end

-- Mains d'ombre qui montent le long du corps jusqu'au cou (Kage Kubishibari)
local function DrawChoke(rec, target, t, el)
	local feet = Feet(target)
	local neck = NARA.NeckPos(target)
	local axis = neck - feet
	local height = axis:Length()
	if height < 1 then return end
	axis:Normalize()
	local ref = math.abs(axis.z) > 0.9 and Vector(1, 0, 0) or UP
	local e1 = axis:Cross(ref):GetNormalized()
	local e2 = axis:Cross(e1):GetNormalized()
	local climb = easeOut(el / C.ChokeClimbTime)
	local squeeze = el > C.ChokeClimbTime and (0.85 + 0.15 * math.sin(t * 14)) or 1
	local N = C.ChokeTendrils

	for i = 1, N do
		local th0 = (i / N) * math.pi * 2 + rec.seed * 0.1
		local spiral = 1.6 + 0.4 * math.sin(i * 1.7)
		local function P(h)
			local th = th0 + spiral * h
			local r = Lerp(h, 15, 4.6 * squeeze) * (1 + 0.08 * math.sin(t * 5 + i + h * 6))
			return feet + axis * (h * height) + (e1 * math.cos(th) + e2 * math.sin(th)) * r, th
		end
		local hmax = math.Clamp(climb * (0.94 + 0.06 * math.sin(i)), 0.02, 1)
		local K = 18
		render.SetMaterial(MAT.strand)
		render.StartBeam(K + 1)
		for k = 0, K do
			local h = hmax * k / K
			local w = Lerp(k / K, 7, 3.2)
			render.AddBeam(P(h), w, h * 3 - t * 0.6, Color(0, 0, 0, 245))
		end
		render.EndBeam()

		-- la main au bout du bras d'ombre
		local hp, th = P(hmax)
		local hp2 = P(math.max(0, hmax - 0.04))
		local tang = (hp - hp2):GetNormalized()
		local out = (e1 * math.cos(th) + e2 * math.sin(th))
		local right = tang:Cross(out):GetNormalized()
		local hs = el > C.ChokeClimbTime and 7.5 or 9.5
		local c = hp + tang * hs * 0.55 + out * 0.6
		render.SetMaterial(MAT.hand)
		mesh.Begin(MATERIAL_QUADS, 1)
		mesh.Position(c - right * hs * 0.5 - tang * hs * 0.6) mesh.TexCoord(0, 0, 1) mesh.Color(0, 0, 0, 250) mesh.AdvanceVertex()
		mesh.Position(c - right * hs * 0.5 + tang * hs * 0.6) mesh.TexCoord(0, 0, 0) mesh.Color(0, 0, 0, 250) mesh.AdvanceVertex()
		mesh.Position(c + right * hs * 0.5 + tang * hs * 0.6) mesh.TexCoord(0, 1, 0) mesh.Color(0, 0, 0, 250) mesh.AdvanceVertex()
		mesh.Position(c + right * hs * 0.5 - tang * hs * 0.6) mesh.TexCoord(0, 1, 1) mesh.Color(0, 0, 0, 250) mesh.AdvanceVertex()
		mesh.End()
	end
end

-- Aiguilles d'ombre qui jaillissent du sol (Kage Nui)
local NUI_BONES = { "ValveBiped.Bip01_Spine2", "ValveBiped.Bip01_Spine4", "ValveBiped.Bip01_Pelvis",
	"ValveBiped.Bip01_R_UpperArm", "ValveBiped.Bip01_L_UpperArm", "ValveBiped.Bip01_R_Thigh", "ValveBiped.Bip01_L_Thigh",
	"ValveBiped.Bip01_R_Forearm", "ValveBiped.Bip01_L_Forearm", "ValveBiped.Bip01_R_Calf", "ValveBiped.Bip01_L_Calf" }

local function NeedleSetup(rec, target, line)
	local list = {}
	local r = rec.seed
	local function rnd(a, b) r = (r * 16807) % 2147483647 return a + (b - a) * (r / 2147483647) end
	local feet = Feet(target)
	local center = target:WorldSpaceCenter()
	for i = 1, C.NuiNeedles do
		local g
		if line and #line > 4 and i % 3 == 0 then
			g = line[math.max(1, #line - math.floor(rnd(2, math.min(#line - 1, 10))))]
		else
			local a = rnd(0, math.pi * 2)
			local d = rnd(28, 70)
			g = NARA.Ground(feet + Vector(math.cos(a) * d, math.sin(a) * d, 0), 30, 80) or feet
		end
		local bone = target:LookupBone(NUI_BONES[(i - 1) % #NUI_BONES + 1])
		list[i] = { g = g, bone = bone, jit = Vector(rnd(-3, 3), rnd(-3, 3), rnd(-4, 4)),
			delay = (i - 1) * 0.012, lift = rnd(0.25, 0.6), fallback = center + Vector(rnd(-6, 6), rnd(-6, 6), rnd(-20, 16)) }
	end
	return list
end

local function DrawNeedles(rec, target, t, el)
	rec.needles = rec.needles or NeedleSetup(rec, target, rec.drawPts)
	local hold = C.NuiHoldTime
	for _, nd in ipairs(rec.needles) do
		local hit = nd.bone and target:GetBonePosition(nd.bone)
		if not hit or hit == target:GetPos() then hit = nd.fallback end
		hit = hit + nd.jit
		local g = nd.g
		local grow = easeOut((el - nd.delay) / 0.16)
		if el > hold then grow = grow * (1 - ease((el - hold) / 0.3)) end
		if grow > 0.01 then
			local dir = (hit - g)
			local dist = dir:Length()
			dir:Normalize()
			local tipEnd = hit + dir * 9                                  -- traverse la cible
			local ctrl = g + UP * dist * nd.lift + (hit - g) * 0.15
			local K = 10
			render.SetMaterial(MAT.needle)
			render.StartBeam(K + 1)
			for k = 0, K do
				local f = (k / K) * grow
				local a = LerpVector(f, g, ctrl)
				local b = LerpVector(f, ctrl, tipEnd)
				local p = LerpVector(f, a, b)
				render.AddBeam(p, Lerp(k / K, 5.5, 0.35), f, Color(0, 0, 0, 250))
			end
			render.EndBeam()
			GroundQuad(MAT.pool, g, 7 * grow, nd.delay * 900, Color(0, 0, 0, 220))
			if grow > 0.98 and not nd.splashed then
				nd.splashed = true
				NARA.InkSplash(hit, dir)
			end
		end
	end
end

-- ---------------------------------------------------------------- particules

local emitter
local function Emitter(pos)
	if not emitter or not emitter:IsValid() then emitter = ParticleEmitter(pos, false) end
	emitter:SetPos(pos)
	return emitter
end

local function Wisp(pos, vel, size, alpha, life)
	local p = Emitter(pos):Add(WISP, pos)
	if not p then return end
	p:SetVelocity(vel)
	p:SetDieTime(life)
	p:SetStartAlpha(alpha)
	p:SetEndAlpha(0)
	p:SetStartSize(size)
	p:SetEndSize(size * 2.2)
	p:SetRoll(math.Rand(0, 360))
	p:SetRollDelta(math.Rand(-1.2, 1.2))
	p:SetColor(0, 0, 0)
	p:SetAirResistance(40)
	p:SetGravity(Vector(0, 0, 6))
	p:SetLighting(false)
end

function NARA.InkSplash(pos, dir)
	for i = 1, 10 do
		local p = Emitter(pos):Add(WISP, pos)
		if p then
			p:SetVelocity((dir * 0.6 + VectorRand() * 0.8) * math.Rand(60, 160))
			p:SetDieTime(math.Rand(0.4, 0.8))
			p:SetStartAlpha(255)
			p:SetEndAlpha(0)
			p:SetStartSize(math.Rand(1.2, 2.6))
			p:SetEndSize(0.5)
			p:SetColor(0, 0, 0)
			p:SetGravity(Vector(0, 0, -380))
			p:SetCollide(true)
			p:SetBounce(0.1)
			p:SetLighting(false)
		end
	end
	for i = 1, 4 do Wisp(pos, VectorRand() * 20, math.Rand(4, 7), 170, math.Rand(0.4, 0.7)) end
end

local function Burst(center, radius, count)
	for i = 1, count do
		local a = math.Rand(0, math.pi * 2)
		local d = Vector(math.cos(a), math.sin(a), 0)
		Wisp(center + d * radius * math.Rand(0.6, 1) + UP * 2, d * math.Rand(40, 110) + UP * math.Rand(10, 40),
			math.Rand(6, 12), 190, math.Rand(0.6, 1.1))
	end
end

local function EmitAlong(rec, pts, dt)
	if not pts or #pts < 2 then return end
	local moving = rec.phase == NARA.PH_STEER or rec.phase == NARA.PH_TRAVEL
	rec.accTip = (rec.accTip or 0) + dt * (moving and 46 or 0)
	rec.accEdge = (rec.accEdge or 0) + dt * math.min(60, #pts * 0.6)
	local tip = pts[#pts]
	while rec.accTip >= 1 do
		rec.accTip = rec.accTip - 1
		Wisp(tip + VectorRand() * 5 + UP * 2, VectorRand() * 9 + UP * math.Rand(8, 24), math.Rand(4, 8), 150, math.Rand(0.5, 1.0))
	end
	while rec.accEdge >= 1 do
		rec.accEdge = rec.accEdge - 1
		local i = math.random(1, #pts)
		local p = pts[i]
		Wisp(p + Vector(math.Rand(-1, 1), math.Rand(-1, 1), 0) * C.Width * 0.8 + UP * 1.5, VectorRand() * 4 + UP * math.Rand(4, 14),
			math.Rand(3.5, 6.5), 95, math.Rand(0.7, 1.3))
	end
end

-- ---------------------------------------------------------------- mise a jour + rendu

local function UpdateWeights(rec, dt)
	local k = math.min(1, dt * 7)
	rec.wKneel = Lerp(k, rec.wKneel or 0, NARA.WantKneel(rec) and 1 or 0)
	rec.wArms = Lerp(math.min(1, dt * 9), rec.wArms or 0, NARA.WantArms(rec) and 1 or 0)
end

hook.Add("Think", "NaraKage_ClientThink", function()
	local dt = FrameTime()
	for ply, rec in pairs(Casts) do
		if not IsValid(ply) then
			Casts[ply] = nil
		else
			UpdateWeights(rec, dt)
			if rec.phase == NARA.PH_NONE and rec.wKneel < 0.01 and rec.wArms < 0.01 then
				Casts[ply] = nil
			end
		end
	end
end)

local function PoolAlpha(rec, now)
	local p = rec.phase
	if p == NARA.PH_WINDUP or p == NARA.PH_TRAVEL then return ease((now - rec.localStart) / 0.45) end
	if p == NARA.PH_NONE then return 1 - ease((now - rec.localStart) / 0.3) end
	if p == NARA.PH_RETRACT then
		local len = rec.retractLen or 0
		local dur = len / C.RetractSpeed
		return 1 - ease((now - rec.localStart - dur) / 0.3)
	end
	return 1
end

hook.Add("PostDrawTranslucentRenderables", "NaraKage_Draw", function(depth, sky)
	if depth or sky then return end
	local now = CurTime()
	local t = RealTime()
	local dt = FrameTime()
	for ply, rec in pairs(Casts) do
		if IsValid(ply) then
			local feet = Feet(ply)
			local seed = rec.seed % 100

			-- onde au sol au moment du sceau
			if rec.ringStart then
				local k = (now - rec.ringStart) / 0.75
				if k < 1 then
					GroundQuad(MAT.ring, feet, Lerp(easeOut(k), 12, 120), seed * 3, Color(0, 0, 0, 220 * (1 - k)))
				end
			end

			-- flaque sous le lanceur
			local pa = PoolAlpha(rec, now)
			if pa > 0.01 then
				local grow = rec.phase == NARA.PH_WINDUP and easeOut((now - rec.localStart) / 0.6) or 1
				local r = C.PoolRadius * grow * (1 + 0.04 * math.sin(t * 3 + seed))
				GroundQuad(MAT.pool, feet, r * 1.45, t * 4 + seed, Color(0, 0, 0, 90 * pa))
				GroundQuad(MAT.pool, feet, r, -t * 6 + seed * 2, Color(0, 0, 0, 238 * pa))
			end

			-- la bande d'ombre
			local line = CurrentLine(ply, rec)
			rec.drawPts = line or rec.drawPts
			if rec.phase == NARA.PH_NONE then rec.drawPts = nil end
			local moving = rec.phase == NARA.PH_STEER or rec.phase == NARA.PH_TRAVEL
			if line and #line >= 2 then
				DrawRibbon(line, C.Width * 1.7, 70, t, moving, seed)
				DrawRibbon(line, C.Width, 242, t, moving, seed)
				if moving then DrawFeelers(line, t, seed) end
				EmitAlong(rec, line, dt)
			end

			-- l'ombre sous la cible prise
			local tgt = rec.target
			local linked = rec.phase == NARA.PH_BOUND or rec.phase == NARA.PH_CHOKE or rec.phase == NARA.PH_PIERCE
			if IsValid(tgt) and linked then
				local tf = Feet(tgt)
				local k = easeOut((now - (rec.catchStart or now)) / 0.35)
				GroundQuad(MAT.pool, tf, C.TargetPool * 1.4 * k, t * 5, Color(0, 0, 0, 85))
				GroundQuad(MAT.pool, tf, C.TargetPool * k, -t * 7 + seed, Color(0, 0, 0, 235))
				if rec.burst == "catch" then
					rec.burst = nil
					Burst(tf, C.TargetPool, 34)
				end
				if rec.phase == NARA.PH_CHOKE then
					DrawChoke(rec, tgt, t, now - rec.localStart)
					rec.accChoke = (rec.accChoke or 0) + dt * 20
					while rec.accChoke >= 1 do
						rec.accChoke = rec.accChoke - 1
						Wisp(LerpVector(math.Rand(0, 1), tf, NARA.NeckPos(tgt)) + VectorRand() * 8, UP * math.Rand(6, 16),
							math.Rand(3, 6), 120, math.Rand(0.5, 0.9))
					end
				elseif rec.phase == NARA.PH_PIERCE then
					DrawNeedles(rec, tgt, t, now - rec.localStart)
				end
			end
			if rec.burst == "start" then
				rec.burst = nil
				Burst(feet, C.PoolRadius * 0.8, 26)
			end
		end
	end
end)
