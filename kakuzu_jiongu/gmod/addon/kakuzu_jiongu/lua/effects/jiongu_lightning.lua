-- Effet du Raiton - Gian : lance d'eclair bleue au coeur blanc, trajet en zigzag
local beamMat = Material("trails/electric")
local glowMat = Material("sprites/light_glow02_add")

function EFFECT:Init(data)
	self.StartPos = data:GetStart()
	self.EndPos = data:GetOrigin()
	self.Power = math.max(data:GetMagnitude(), 0.3)
	self.Life = 0.35
	self.DieTime = CurTime() + self.Life
	self:SetRenderBoundsWS(self.StartPos, self.EndPos, Vector(64, 64, 64))
	self.Points = {}
	self:Rebuild()
	self.NextRebuild = CurTime() + 0.04
end

function EFFECT:Rebuild()
	local pts = {}
	local seg = 14
	local dir = self.EndPos - self.StartPos
	local len = dir:Length()
	for i = 0, seg do
		local t = i / seg
		local p = self.StartPos + dir * t
		if i > 0 and i < seg then
			p = p + VectorRand() * len * 0.025 * self.Power
		end
		pts[#pts + 1] = p
	end
	self.Points = pts
end

function EFFECT:Think()
	if CurTime() > self.NextRebuild then
		self:Rebuild()
		self.NextRebuild = CurTime() + 0.04
	end
	return CurTime() < self.DieTime
end

function EFFECT:Render()
	local frac = math.Clamp((self.DieTime - CurTime()) / self.Life, 0, 1)
	local w = 28 * self.Power * frac
	render.SetMaterial(beamMat)
	for pass = 1, 2 do
		local col = pass == 1 and Color(90, 160, 255, 255 * frac) or Color(240, 250, 255, 255 * frac)
		local width = pass == 1 and w or w * 0.35
		render.StartBeam(#self.Points)
		for i, p in ipairs(self.Points) do
			render.AddBeam(p, width, i / #self.Points, col)
		end
		render.EndBeam()
	end
	render.SetMaterial(glowMat)
	render.DrawSprite(self.StartPos, 70 * frac, 70 * frac, Color(140, 200, 255, 255))
	render.DrawSprite(self.EndPos, 110 * frac, 110 * frac, Color(140, 200, 255, 255))
end
