-- Kakuzu : les quatre coeurs (Jiongu) - initialisation partagee
-- Fan-made, non commercial. Naruto (c) Masashi Kishimoto / Shueisha / Studio Pierrot.

JIONGU = JIONGU or {}

JIONGU.Monsters = {
	{ class = "npc_jiongu_katon",  name = "Jiongu - Masque du Feu (Katon)" },
	{ class = "npc_jiongu_futon",  name = "Jiongu - Masque du Vent (Futon)" },
	{ class = "npc_jiongu_raiton", name = "Jiongu - Masque de la Foudre (Raiton)" },
	{ class = "npc_jiongu_suiton", name = "Jiongu - Masque de l'Eau (Suiton)" },
}

-- 1 = les monstres poses depuis le menu PNJ attaquent les joueurs proches
-- 0 = ils n'attaquent que les PNJ et ceux qui les blessent
CreateConVar("jiongu_hostile", "1", bit.bor(FCVAR_ARCHIVE, FCVAR_NOTIFY, FCVAR_REPLICATED),
	"Jiongu : les monstres poses par le menu attaquent les joueurs (1) ou non (0)")
CreateConVar("jiongu_damage_scale", "1", bit.bor(FCVAR_ARCHIVE, FCVAR_NOTIFY, FCVAR_REPLICATED),
	"Jiongu : multiplicateur des degats des techniques")
CreateConVar("jiongu_model_scale", "1", bit.bor(FCVAR_ARCHIVE, FCVAR_NOTIFY, FCVAR_REPLICATED),
	"Jiongu : taille des monstres (1 = taille anime, 0.75 = passe mieux dans les batiments)")

for _, m in ipairs(JIONGU.Monsters) do
	list.Set("NPC", m.class, { Name = m.name, Class = m.class, Category = "Naruto - Kakuzu (Jiongu)" })
end

if SERVER then
	AddCSLuaFile()
	AddCSLuaFile("effects/jiongu_lightning.lua")
	AddCSLuaFile("effects/jiongu_wind.lua")
	-- Serveur dedie : si tu publies l'addon sur le Workshop, ajoute ici resource.AddWorkshop("<ID>")
	-- pour que les joueurs telechargent les modeles et textures automatiquement.

	-- Les monstres invoques protegent leur maitre : celui qui le blesse devient leur cible.
	hook.Add("EntityTakeDamage", "Jiongu_GuardOwner", function(target, dmg)
		if not target:IsPlayer() or not target.JionguMonsters then return end
		local attacker = dmg:GetAttacker()
		if not IsValid(attacker) or attacker == target then return end
		for _, mon in pairs(target.JionguMonsters) do
			if IsValid(mon) and mon ~= attacker and mon.JOwner ~= attacker then
				mon:SetJionguEnemy(attacker)
			end
		end
	end)

	hook.Add("PlayerDisconnected", "Jiongu_Cleanup", function(ply)
		if not ply.JionguMonsters then return end
		for _, mon in pairs(ply.JionguMonsters) do
			if IsValid(mon) then mon:Remove() end
		end
	end)
end

if CLIENT then
	for _, m in ipairs(JIONGU.Monsters) do
		language.Add(m.class, m.name)
	end
	language.Add("jiongu_fireball", "Katon : Zukokku")
	language.Add("jiongu_waterball", "Suiton : Bulle d'eau")
	language.Add("weapon_jiongu", "Jiongu (Kakuzu)")
end
