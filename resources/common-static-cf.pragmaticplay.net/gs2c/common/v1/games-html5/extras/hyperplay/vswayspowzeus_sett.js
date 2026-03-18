var hp_waitForFSOptions = true;
HPVARS.useFoxForSpinResponse = true;

HPVARS.Gamble = {};
HPVARS.Gamble.rootPath = "UI Root/XTRoot/Root/Game/GamePivot/Reels/BonusGame/content/";

HPVARS.Gamble.gamblePaths = ["Wheel/content/GambleButton"];
HPVARS.Gamble.collectPath = "Wheel/content/CollectButton";
HPVARS.Gamble.winPath = HPVARS.Gamble.rootPath + "Indicator/content/Status/Win/text/Label";
HPVARS.Gamble.losePath = HPVARS.Gamble.rootPath + "Indicator/content/Status/Lose/text/Label";

HPVARS.Gamble.gambleColliderClass = CATButton;

HPVARS.Gamble.propNames = ["gamble_lvl_1", "gamble_lvl_2", "gamble_lvl_3", "gamble_lvl_4", "gamble_lvl_5"];
HPVARS.Gamble.optionPaths = ['UI Root/XTRoot/Root/Game/GamePivot/Reels/BonusGame/content/Wheel/content/CollectButton/content/text/freespins/LabelFS'];

HPVARS.Gamble.fsKey = "fs";
HPVARS.Gamble.tryKey = "try";
HPVARS.Gamble.baseNo = 10;
HPVARS.Gamble.max = 30;
HPVARS.Gamble.step = 4;