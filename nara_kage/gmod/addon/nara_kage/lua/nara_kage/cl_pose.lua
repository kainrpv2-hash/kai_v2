-- Nara : pose du lanceur (genou a terre + sceau du Rat) par cinematique inverse.
-- Aucune animation de GMod ne fait ce geste : on part de l'animation de repos
-- et on replace les os dans le callback BuildBonePositions. Le calcul se fait
-- en coordonnees monde a partir des positions reelles des os : il marche sur
-- tous les modeles ValveBiped, quelle que soit leur taille.

NARA = NARA or {}

local BONE = {
	pelvis = "ValveBiped.Bip01_Pelvis",
	spine  = "ValveBiped.Bip01_Spine",
	spine2 = "ValveBiped.Bip01_Spine2",
	spine4 = "ValveBiped.Bip01_Spine4",
	neck   = "ValveBiped.Bip01_Neck1",
	head   = "ValveBiped.Bip01_Head1",
}
for _, s in ipairs({ "R", "L" }) do
	BONE[s .. "thigh"] = "ValveBiped.Bip01_" .. s .. "_Thigh"
	BONE[s .. "calf"]  = "ValveBiped.Bip01_" .. s .. "_Calf"
	BONE[s .. "foot"]  = "ValveBiped.Bip01_" .. s .. "_Foot"
	BONE[s .. "toe"]   = "ValveBiped.Bip01_" .. s .. "_Toe0"
	BONE[s .. "upper"] = "ValveBiped.Bip01_" .. s .. "_UpperArm"
	BONE[s .. "fore"]  = "ValveBiped.Bip01_" .. s .. "_Forearm"
	BONE[s .. "hand"]  = "ValveBiped.Bip01_" .. s .. "_Hand"
	for f = 0, 4 do
		BONE[s .. "f" .. f .. "a"] = "ValveBiped.Bip01_" .. s .. "_Finger" .. f
		BONE[s .. "f" .. f .. "b"] = "ValveBiped.Bip01_" .. s .. "_Finger" .. f .. "1"
		BONE[s .. "f" .. f .. "c"] = "ValveBiped.Bip01_" .. s .. "_Finger" .. f .. "2"
	end
end

-- ---------------------------------------------------------------- maths

-- Rotation 3x3 (formule de Rodrigues), axe normalise, angle en radians
local function RotAxis(k, a)
	local c, s = math.cos(a), math.sin(a)
	local t = 1 - c
	local x, y, z = k.x, k.y, k.z
	return {
		{ c + x * x * t,     x * y * t - z * s, x * z * t + y * s },
		{ y * x * t + z * s, c + y * y * t,     y * z * t - x * s },
		{ z * x * t - y * s, z * y * t + x * s, c + z * z * t     },
	}
end

local function MulRV(R, v)
	return Vector(R[1][1] * v.x + R[1][2] * v.y + R[1][3] * v.z,
		R[2][1] * v.x + R[2][2] * v.y + R[2][3] * v.z,
		R[3][1] * v.x + R[3][2] * v.y + R[3][3] * v.z)
end

-- Plus petite rotation qui amene la direction a sur la direction b
local function RotBetween(a, b, w)
	a = a:GetNormalized()
	b = b:GetNormalized()
	local axis = a:Cross(b)
	local s = axis:Length()
	local c = math.Clamp(a:Dot(b), -1, 1)
	if s < 1e-6 then
		if c > 0 then return nil end
		-- demi-tour : n'importe quel axe perpendiculaire
		axis = math.abs(a.z) < 0.9 and a:Cross(Vector(0, 0, 1)) or a:Cross(Vector(1, 0, 0))
		axis:Normalize()
		return RotAxis(axis, math.pi * (w or 1))
	end
	return RotAxis(axis / s, math.atan2(s, c) * (w or 1))
end

-- Rotation qui amene le repere (f1, p1) sur (f2, p2), ponderee par w (axe-angle)
local function Comps(v) return { v.x, v.y, v.z } end

local function RotFrames(f1, p1, f2, p2, w)
	local c1 = { Comps(f1), Comps(p1), Comps(f1:Cross(p1)) }
	local c2 = { Comps(f2), Comps(p2), Comps(f2:Cross(p2)) }
	local R = { { 0, 0, 0 }, { 0, 0, 0 }, { 0, 0, 0 } }
	for i = 1, 3 do
		for j = 1, 3 do
			local v = 0
			for k = 1, 3 do v = v + c2[k][i] * c1[k][j] end
			R[i][j] = v
		end
	end
	if w >= 0.999 then return R end
	local tr = R[1][1] + R[2][2] + R[3][3]
	local ang = math.acos(math.Clamp((tr - 1) / 2, -1, 1))
	if ang < 1e-4 then return nil end
	local axis = Vector(R[3][2] - R[2][3], R[1][3] - R[3][1], R[2][1] - R[1][2])
	if axis:Length() < 1e-5 then return R end
	axis:Normalize()
	return RotAxis(axis, ang * w)
end

-- ---------------------------------------------------------------- squelette

local Subtrees = {}

local function Subtree(ent, bone)
	local mdl = ent:GetModel() or ""
	Subtrees[mdl] = Subtrees[mdl] or {}
	local list = Subtrees[mdl][bone]
	if list then return list end
	list = {}
	local stack = { bone }
	while #stack > 0 do
		local b = table.remove(stack)
		list[#list + 1] = b
		for _, c in ipairs(ent:GetChildBones(b) or {}) do stack[#stack + 1] = c end
	end
	Subtrees[mdl][bone] = list
	return list
end

local function Pos(ent, b)
	local m = b and ent:GetBoneMatrix(b)
	return m and m:GetTranslation()
end

-- Tourne l'os et tous ses enfants autour du point pivot
local function ApplyRot(ent, bone, R, pivot)
	if not R or not bone then return end
	local rp = MulRV(R, pivot)
	local D = Matrix({
		{ R[1][1], R[1][2], R[1][3], pivot.x - rp.x },
		{ R[2][1], R[2][2], R[2][3], pivot.y - rp.y },
		{ R[3][1], R[3][2], R[3][3], pivot.z - rp.z },
		{ 0, 0, 0, 1 },
	})
	for _, b in ipairs(Subtree(ent, bone)) do
		local m = ent:GetBoneMatrix(b)
		if m then ent:SetBoneMatrix(b, D * m) end
	end
end

local function Translate(ent, roots, offset)
	local D = Matrix()
	D:SetTranslation(offset)
	for _, r in ipairs(roots) do
		for _, b in ipairs(Subtree(ent, r)) do
			local m = ent:GetBoneMatrix(b)
			if m then ent:SetBoneMatrix(b, D * m) end
		end
	end
end

-- Oriente l'os pour que (enfant - os) pointe vers dir
local function Aim(ent, bone, child, dir, w)
	local p, c = Pos(ent, bone), Pos(ent, child)
	if not p or not c then return end
	ApplyRot(ent, bone, RotBetween(c - p, dir, w), p)
end

-- IK a deux os (cuisse/mollet ou bras/avant-bras). pole = direction du coude / genou.
local function TwoBone(ent, bA, bB, bC, target, pole, w)
	local A, B, C = Pos(ent, bA), Pos(ent, bB), Pos(ent, bC)
	if not A or not B or not C then return end
	local L1, L2 = A:Distance(B), B:Distance(C)
	local T = LerpVector(w, C, target)
	local toT = T - A
	local d = math.Clamp(toT:Length(), math.abs(L1 - L2) + 0.05, (L1 + L2) * 0.999)
	local dir = toT:GetNormalized()
	local cur = (B - A) - dir * (B - A):Dot(dir)
	local pl = pole - dir * pole:Dot(dir)
	if cur:LengthSqr() > 1e-6 then
		cur:Normalize()
		if pl:LengthSqr() > 1e-6 then pl = LerpVector(w, cur, pl:GetNormalized()) else pl = cur end
	end
	if pl:LengthSqr() < 1e-6 then return end
	pl:Normalize()
	local a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
	local h = math.sqrt(math.max(0, L1 * L1 - a * a))
	local knee = A + dir * a + pl * h
	ApplyRot(ent, bA, RotBetween(B - A, knee - A), A)
	local B2, C2 = Pos(ent, bB), Pos(ent, bC)
	ApplyRot(ent, bB, RotBetween(C2 - B2, A + dir * d - B2), B2)
end

-- Plie un doigt (3 phalanges) vers la paume
local function Curl(ent, ids, palm, angles, w)
	local seg
	for i = 1, 3 do
		local b, nxt = ids[i], ids[i + 1]
		local p = Pos(ent, b)
		if not p then return end
		local c = Pos(ent, nxt)
		if c then seg = c - p end          -- derniere phalange : direction de la precedente
		if not seg then return end
		local axis = seg:Cross(palm)
		if axis:LengthSqr() > 1e-6 then
			axis:Normalize()
			ApplyRot(ent, b, RotAxis(axis, math.rad(angles[i]) * w), p)
		end
	end
end

-- Tend un doigt dans la direction dir
local function Straight(ent, ids, dir, w)
	for i = 1, 2 do
		if ids[i] and ids[i + 1] then Aim(ent, ids[i], ids[i + 1], dir, w) end
	end
end

-- ---------------------------------------------------------------- la pose

local function BuildPose(ent, wk, wa)
	local b = {}
	for k, name in pairs(BONE) do
		local id = ent:LookupBone(name)
		if id and id >= 0 then b[k] = id end
	end
	if not b.pelvis then return end
	for _, s in ipairs({ "R", "L" }) do
		if not (b[s .. "thigh"] and b[s .. "calf"] and b[s .. "foot"]) then wk = 0 end
	end

	local O = ent:GetPos()
	local yaw = ent:GetRenderAngles().y
	local F = Angle(0, yaw, 0):Forward()
	local U = Vector(0, 0, 1)
	local Rt = F:Cross(U)
	local C = NARA.Config

	-- ---- genou a terre
	if wk > 0.001 then
		local K = C.KneelLeg == "L" and "L" or "R"   -- jambe dont le genou touche le sol
		local P = K == "R" and "L" or "R"            -- jambe avant, pied a plat
		local kSide = K == "R" and 1 or -1

		local hipK = Pos(ent, b[K .. "thigh"])
		local L1 = hipK:Distance(Pos(ent, b[K .. "calf"]))
		local L2 = Pos(ent, b[K .. "calf"]):Distance(Pos(ent, b[K .. "foot"]))
		local ankleH = math.max(2, Pos(ent, b[P .. "foot"]).z - O.z)
		local footDir = b[P .. "toe"] and (Pos(ent, b[P .. "toe"]) - Pos(ent, b[P .. "foot"])) or nil

		-- descend tout le corps : la hanche passe a hauteur de cuisse au-dessus du sol
		local drop = math.max(0, (hipK.z - O.z) - (L1 * 0.96 + 2.5))
		local roots = {}
		for i = 0, ent:GetBoneCount() - 1 do
			if ent:GetBoneParent(i) < 0 then roots[#roots + 1] = i end
		end
		Translate(ent, roots, -U * drop * wk + F * (-2 * wk))

		-- buste legerement penche en avant, tete vers l'ombre
		if b.spine then
			ApplyRot(ent, b.spine, RotAxis(U:Cross(F):GetNormalized(), math.rad(11) * wk), Pos(ent, b.spine))
		end
		if b.head then
			ApplyRot(ent, b.head, RotAxis(U:Cross(F):GetNormalized(), math.rad(9) * wk), Pos(ent, b.head))
		end

		-- jambe du genou : cuisse verticale, tibia allonge vers l'arriere sur le sol
		local hip = Pos(ent, b[K .. "thigh"])
		local kneeT = Vector(hip.x, hip.y, O.z + 2.5) + F * 2 + Rt * kSide * 1.5
		local ankleT = kneeT - F * (L2 * 0.96) + U * 3.5 + Rt * kSide * 2
		TwoBone(ent, b[K .. "thigh"], b[K .. "calf"], b[K .. "foot"], ankleT, kneeT - hip, wk)
		if b[K .. "toe"] then
			Aim(ent, b[K .. "foot"], b[K .. "toe"], -U * 0.75 - F * 0.66, wk)  -- orteils retournes au sol
		end

		-- jambe avant : pied a plat devant, genou leve
		local hipP = Pos(ent, b[P .. "thigh"])
		local L1p = hipP:Distance(Pos(ent, b[P .. "calf"]))
		local footT = Vector(hipP.x, hipP.y, O.z + ankleH) + F * (L1p * 0.82) - Rt * kSide * 2.5
		TwoBone(ent, b[P .. "thigh"], b[P .. "calf"], b[P .. "foot"], footT, F + U * 0.7, wk)
		if footDir and b[P .. "toe"] then
			Aim(ent, b[P .. "foot"], b[P .. "toe"], footDir, wk)
		end
	end

	-- ---- sceau du Rat (Ne) : mains jointes devant la poitrine, index et majeur tendus
	if wa > 0.001 and b.Rupper and b.Lupper and b.Rhand and b.Lhand and b.neck and b.spine then
		local neck = Pos(ent, b.neck)
		local up = (neck - Pos(ent, b.spine)):GetNormalized()
		local fw = (F - up * F:Dot(up)):GetNormalized()
		local rt = fw:Cross(up)
		local H = neck - up * 6.5 + fw * 13          -- point de contact des mains

		local fingersDir = (up * 0.93 + fw * 0.36):GetNormalized()
		for _, s in ipairs({ "R", "L" }) do
			local side = s == "R" and 1 or -1
			local wrist = H + rt * side * 1.7 - up * 4.2 + fw * side * 0.7
			local pole = rt * side - up * 0.9 - fw * 0.15
			TwoBone(ent, b[s .. "upper"], b[s .. "fore"], b[s .. "hand"], wrist, pole, wa)

			-- orientation de la main : doigts vers le haut, paume vers l'autre main
			local hp = Pos(ent, b[s .. "hand"])
			local mid = Pos(ent, b[s .. "f2a"])
			local idx, pky = Pos(ent, b[s .. "f1a"]), Pos(ent, b[s .. "f4a"])
			if hp and mid and idx and pky then
				local f = (mid - hp):GetNormalized()
				local across = idx - pky
				local palm = side > 0 and -f:Cross(across) or f:Cross(across)
				palm = (palm - f * palm:Dot(f)):GetNormalized()
				local palmT = -rt * side
				palmT = (palmT - fingersDir * palmT:Dot(fingersDir)):GetNormalized()
				ApplyRot(ent, b[s .. "hand"], RotFrames(f, palm, fingersDir, palmT, wa), hp)

				-- doigts : index + majeur tendus, annulaire + auriculaire + pouce replies
				local palmNow = LerpVector(wa, palm, palmT):GetNormalized()
				Straight(ent, { b[s .. "f1a"], b[s .. "f1b"], b[s .. "f1c"] }, fingersDir, wa)
				Straight(ent, { b[s .. "f2a"], b[s .. "f2b"], b[s .. "f2c"] }, fingersDir, wa)
				Curl(ent, { b[s .. "f3a"], b[s .. "f3b"], b[s .. "f3c"] }, palmNow, { 78, 88, 60 }, wa)
				Curl(ent, { b[s .. "f4a"], b[s .. "f4b"], b[s .. "f4c"] }, palmNow, { 82, 88, 60 }, wa)
				Curl(ent, { b[s .. "f0a"], b[s .. "f0b"], b[s .. "f0c"] }, palmNow, { 30, 35, 25 }, wa)
			end
		end
	end
end

NARA.BuildPose = BuildPose

local function PoseCallback(ent)
	local rec = NARA.Casts and NARA.Casts[ent]
	if not rec then
		-- la cible prise par Kagemane imite aussi le sceau de son lanceur
		local by = ent.GetNW2Entity and ent:GetNW2Entity("NaraBy")
		local brec = IsValid(by) and NARA.Casts[by]
		if brec and brec.phase == NARA.PH_BOUND and (brec.wArms or 0) > 0.001 then BuildPose(ent, 0, brec.wArms) end
		return
	end
	local wk, wa = rec.wKneel or 0, rec.wArms or 0
	if wk < 0.001 and wa < 0.001 then return end
	BuildPose(ent, wk, wa)
end

function NARA.EnsurePoseCallback(ply)
	if not IsValid(ply) or ply.NaraPoseCB then return end
	ply.NaraPoseCB = ply:AddCallback("BuildBonePositions", PoseCallback)
end
