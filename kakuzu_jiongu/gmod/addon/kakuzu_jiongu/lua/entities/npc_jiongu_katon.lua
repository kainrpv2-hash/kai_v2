-- Masque du Feu : Katon - Zukokku (boule de feu qui explose en tempete de flammes)
AddCSLuaFile()

ENT.Base = "npc_jiongu_base"
ENT.Type = "nextbot"
ENT.PrintName = "Jiongu - Masque du Feu (Katon)"
ENT.Spawnable = false -- apparait dans l'onglet PNJ (voir autorun/jiongu_init.lua)

ENT.JModel = "models/kakuzu_jiongu/jiongu_katon.mdl"
ENT.JElement = "katon"
ENT.JHealth = 900
ENT.JSpeed = 130
ENT.JRange = 1300
ENT.JCooldown = 5
ENT.JMaskHeight = 94
ENT.JHull = 44
ENT.JHullHeight = 125

if SERVER then
	function ENT:FireJutsu(target)
		local start = self:MaskPos()
		local aim = (target:WorldSpaceCenter() - start):GetNormalized()
		local ball = ents.Create("jiongu_fireball")
		if not IsValid(ball) then return end
		ball:SetPos(start + aim * 30)
		ball:SetAngles(aim:Angle())
		ball.JMonster = self
		ball.JAttacker = IsValid(self.JOwner) and self.JOwner or self
		ball:Spawn()
		ball:Launch(aim * 1100)
		self:EmitSound("ambient/fire/gascan_ignite1.wav", 90, 80)
	end
end
