-- Effet du Futon - Atsugai : onde d'air comprime en cone devant le masque
local ringMat = Material("effects/select_ring")
local dustMat = Material("particle/particle_smokegrenade")

function EFFECT:Init(data)
	self.Origin = data:GetOrigin()
	self.Dir = data:GetNormal()
	self.Range = data:GetMagnitude()
	self.Life = 0.7
	self.Born = CurTime()
	self:SetRenderBoundsWS(self.Origin - Vector(1, 1, 1) * self.Range, self.Origin + Vector(1, 1, 1) * self.Range)
	local emitter = ParticleEmitter(self.Origin)
	if emitter then
		for i = 1, 60 do
			local spread = (self.Dir + VectorRand() * 0.35):GetNormalized()
			local p = emitter:Add(dustMat, self.Origin + spread * math.Rand(10, 60))
			if p then
				p:SetVelocity(spread * math.Rand(900, 1600))
				p:SetAirResistance(140)
				p:SetDieTime(math.Rand(0.6, 1.1))
				p:SetStartAlpha(110)
				p:SetEndAlpha(0)
				p:SetStartSize(math.Rand(20, 40))
				p:SetEndSize(math.Rand(140, 220))
				p:SetRoll(math.Rand(0, 360))
				p:SetRollDelta(math.Rand(-2, 2))
				p:SetColor(225, 228, 235)
			end
		end
		emitter:Finish()
	end
end

function EFFECT:Think()
	return CurTime() - self.Born < self.Life
end

function EFFECT:Render()
	local t = (CurTime() - self.Born) / self.Life
	render.SetMaterial(ringMat)
	for k = 0, 2 do
		local tt = math.Clamp(t - k * 0.12, 0, 1)
		if tt > 0 then
			local pos = self.Origin + self.Dir * self.Range * tt * 0.8
			local size = 60 + self.Range * 0.7 * tt
			render.DrawQuadEasy(pos, -self.Dir, size, size, Color(235, 240, 255, 200 * (1 - tt)), CurTime() * 90)
		end
	end
end
