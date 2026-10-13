-- Masque de l'Eau : Suiton
-- L'anime ne lui montre aucune technique (il meurt avant d'attaquer). Pour le RP, on lui donne une
-- bulle d'eau sous pression qui repousse, eteint le feu et fait des degats moderes.
AddCSLuaFile()

ENT.Base = "npc_jiongu_base"
ENT.Type = "nextbot"
ENT.PrintName = "Jiongu - Masque de l'Eau (Suiton)"
ENT.Spawnable = false

ENT.JModel = "models/kakuzu_jiongu/jiongu_suiton.mdl"
ENT.JElement = "suiton"
ENT.JHealth = 800
ENT.JSpeed = 140
ENT.JRange = 1200
ENT.JCooldown = 3.5
ENT.JMaskHeight = 96
ENT.JHull = 40
ENT.JHullHeight = 120

if SERVER then
	function ENT:FireJutsu(target)
		local start = self:MaskPos()
		local aim = (target:WorldSpaceCenter() - start):GetNormalized()
		local ball = ents.Create("jiongu_waterball")
		if not IsValid(ball) then return end
		ball:SetPos(start + aim * 30)
		ball.JMonster = self
		ball.JAttacker = IsValid(self.JOwner) and self.JOwner or self
		ball:Spawn()
		ball:Launch(aim * 1300)
		self:EmitSound("ambient/water/water_splash" .. math.random(1, 3) .. ".wav", 90, 70)
	end
end
