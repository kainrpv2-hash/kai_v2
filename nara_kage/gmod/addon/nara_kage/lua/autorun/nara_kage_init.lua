-- Nara : manipulation des ombres - chargement
-- Fan-made, non commercial. Naruto (c) Masashi Kishimoto / Shueisha / Studio Pierrot.

NARA = NARA or {}

local SHARED = { "nara_kage/sh_config.lua", "nara_kage/sh_core.lua" }
local CLIENT_FILES = { "nara_kage/cl_pose.lua", "nara_kage/cl_fx.lua", "nara_kage/cl_view.lua" }

if SERVER then
	for _, f in ipairs(SHARED) do AddCSLuaFile(f) end
	for _, f in ipairs(CLIENT_FILES) do AddCSLuaFile(f) end
	-- Serveur dedie : si tu publies l'addon sur le Workshop, ajoute ici resource.AddWorkshop("<ID>")
	-- pour que les joueurs telechargent les textures et les sons automatiquement.
end

for _, f in ipairs(SHARED) do include(f) end

if SERVER then
	include("nara_kage/sv_core.lua")
else
	for _, f in ipairs(CLIENT_FILES) do include(f) end
	language.Add("weapon_nara_kage", "Hiden : Ombres (Nara)")
end
