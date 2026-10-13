-- Masque de la Foudre : Raiton - Gian (lances d'eclairs qui jaillissent de la bouche)
AddCSLuaFile()

ENT.Base = "npc_jiongu_base"
ENT.Type = "nextbot"
ENT.PrintName = "Jiongu - Masque de la Foudre (Raiton)"
ENT.Spawnable = false

ENT.JModel = "models/kakuzu_jiongu/jiongu_raiton.mdl"
ENT.JElement = "raiton"
ENT.JHealth = 1100
ENT.JSpeed = 120
ENT.JRange = 1500
ENT.JCooldown = 4
ENT.JMaskHeight = 102
ENT.JHull = 50
ENT.JHullHeight = 135

if SERVER then
	function ENT:FireJutsu(target)
		local start = self:MaskPos()
		local filter = { self }
		-- une lance principale + deux lances qui se separent (comme dans l'episode 84)
		local spears = { 0, -1, 1 }
		for i, side in ipairs(spears) do
			timer.Simple((i - 1) * 0.12, function()
				if not IsValid(self) then return end
				local aimAt = IsValid(target) and target:WorldSpaceCenter() or (start + self:GetForward() * 800)
				local dir = (aimAt - start):GetNormalized()
				if side ~= 0 then
					dir = (dir + self:GetRight() * side * 0.06 + VectorRand() * 0.02):GetNormalized()
				end
				local tr = util.TraceLine({ start = start, endpos = start + dir * self.JRange, filter = filter, mask = MASK_SHOT })
				local ed = EffectData()
				ed:SetStart(start)
				ed:SetOrigin(tr.HitPos)
				ed:SetMagnitude(side == 0 and 1 or 0.6)
				util.Effect("jiongu_lightning", ed, true, true)
				local hit = tr.Entity
				if IsValid(hit) and not self:IsFriend(hit) then
					self:Damage(hit, side == 0 and 70 or 30, DMG_SHOCK, dir * 8000)
				end
				for _, ent in ipairs(ents.FindInSphere(tr.HitPos, 90)) do
					if IsValid(ent) and ent ~= hit and not self:IsFriend(ent) and (ent:IsPlayer() or ent:IsNPC() or ent:IsNextBot()) then
						self:Damage(ent, 15, DMG_SHOCK, dir * 2000)
					end
				end
				local spark = EffectData()
				spark:SetOrigin(tr.HitPos)
				spark:SetNormal(tr.HitNormal)
				spark:SetMagnitude(4)
				spark:SetScale(2)
				spark:SetRadius(8)
				util.Effect("Sparks", spark, true, true)
				sound.Play("ambient/energy/zap" .. math.random(1, 9) .. ".wav", tr.HitPos, 90, math.random(80, 110))
			end)
		end
		self:EmitSound("ambient/energy/weld" .. math.random(1, 2) .. ".wav", 95, 70)
	end
end
