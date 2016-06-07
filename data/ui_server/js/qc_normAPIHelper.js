var BrowseRootPath = "/api/results/browse/";
var mockBrowseRootPath = "/Datax/browse.json";
var mockProjectRunsPath = "/Datax/runs.json";
var mockRunPath = "/Datax/run.json";
var mockPhenotypes = "/Datax/phenotypes.json";
var mockPlates = "/Datax/plates.json";
var mockPlateData = "/Datax/Plate1.json";
var mockGtPlateData = "/Datax/gtPlate1.json";
var mockYieldPlateData = "/Datax/yieldPlate1.json";
var mackExperiment0_0 = "/Datax/experiment_0_0.json";

function BrowseProjectsRoot(isDebug, callback) {
    var path;
    if (isDebug) path = mockBrowseRootPath;
    else path = BrowseRootPath;

    d3.json(path, function(error, json) {
        if (error) return console.warn(error);
        else {
            var names = json.names;
            var urls = json.urls;
            var len = names.length;
            var projects = [];
            for (var i = 0; i < len; i++) {
                var projectUrl = urls[i];
                var projectName;
                if (names[i] == null)
                    projectName = "[" + getLastSegmentOfPath(projectUrl) + "]";
                else projectName = names[i];
                var project = { name: projectName, url: projectUrl }
                projects.push(project);
            }
            callback(projects);
        }
    });
};

function BrowsePath(isDebug, url, callback) {
    var path;
    if (isDebug) path = mockRunPath;
    else path = url.replace("ch", "");

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            var names = json.names;
            var urls = json.urls;
            var isProject = json.is_project;
            var len = names.length;
            var paths = [];
            for (var i = 0; i < len; i++) {
                var folder = getLastSegmentOfPath(urls[i]);
                var path = { name: names[i] + " [" + folder + "]", url: urls[i] }
                paths.push(path);
            }
            var projectDetails="";
            if (isProject) {
                projectDetails = { 
                    analysis_date: json.analysis_date,
                    analysis_instructions: json.analysis_instructions,
                    change_date: json.change_date,
                    extraction_date: json.extraction_date,
                    phenotype_names: json.phenotype_names,
                    project_name: json.project_name,
                    project: json.project
                }
            }
            var browse = { isProject: isProject, paths: paths, projectDetails: projectDetails }
            callback(browse);
        }
    });
};

function GetProjectRuns(isDebug, url, callback) {
    var path;
    if (isDebug) path = mockProjectRunsPath;
    else path = url;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            var names = json.names;
            var urls = json.urls;
            var len = names.length;
            var projects = [];
            for (var i = 0; i < len; i++) {
                var folder = getLastSegmentOfPath(urls[i]);
                var project = { name: names[i] + " ["+folder+"]", url: urls[i] }
                projects.push(project);
            }
            callback(projects);
        }
    });
};

function GetRunPhenotypePath(isDebug, url, callback) {
    var path;
    if (isDebug) path = mockRunPath;
    else path = url;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            var phenoPath = json.phenotype_names;
            callback(phenoPath);
        }
    });
};

function GetRunPhenotypes(isDebug, url, callback) {
    var path;
    if (isDebug) path = mockPhenotypes;
    else path = url;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            var phenotypes = [];
            for (var i = 0; i < json.phenotypes.length; i++) {
                phenotypes.push({ name: json.phenotypes[i], url: json.phenotype_urls[i] });
            }
            callback(phenotypes);
        }
    });
};

function GetPhenotypesPlates(isDebug, url, callback) {
    var path;
    if (isDebug)
        path = mockPlates;
    else
        path = url;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            var plates = [];
            for (var i = 0; i < json.urls.length; i++) {
                plates.push({ index: json.plate_indices[i], url: json.urls[i] });
            }
            callback(plates);
        }
    });
};

function GetPlateData(isDebug, url, metaDataPath, phenotypePlaceholderMetaDataPath, callback) {
    var path;
    if (isDebug) path = mockPlateData;
    else path = url;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            GetGtPlateData(isDebug,metaDataPath,phenotypePlaceholderMetaDataPath, function(gtData) {
                GetGtWhenPlateData(isDebug, metaDataPath, phenotypePlaceholderMetaDataPath, function (gtWhenData) {
                    GetYieldPlateData(isDebug, metaDataPath, phenotypePlaceholderMetaDataPath, function (yieldData) {
                        var plate = {
                            plate_data: json.data,
                            Plate_metadata : {
                                plate_BadData: json.BadData,
                                plate_Empty: json.Empty,
                                plate_NoGrowth: json.NoGrowth,
                                plate_UndecidedProblem: json.UndecidedProblem
                            },
                            Growth_metaData: {
                                gt: gtData,
                                gtWhen: gtWhenData,
                                yld: yieldData
                            }
                        }
                        callback(plate);
                    });
                });
            });
           
        }
    });
};

function GetGtPlateData(isDebug, url, placeholder, callback) {
    var path;
    if (isDebug) path = mockPlateData;
    else path = url.replace(placeholder, "GenerationTime");
    console.log("Metadata GTWhen Path:" + path);
    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            callback(json.data);
        }
    });
};

function GetGtWhenPlateData(isDebug, url, placeholder, callback) {
    var path;
    if (isDebug) path = mockGtPlateData;
    else path = url.replace(placeholder, "GenerationTimeWhen");
    console.log("Metadata GTWhen Path:" + path);
    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            callback(json.data);
        }
    });
};

function GetYieldPlateData(isDebug, url, placeholder, callback) {
    var path;
    if (isDebug) path = mockYieldPlateData;
    else path = url.replace(placeholder, "ExperimentGrowthYield");
    console.log("Metadata yield path:" + path);

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
            callback(json.data);
        }
    });
};

function GetExperimentGrowthData(isDebug, plateUrl, callback) {
    var path;
    if (isDebug) path = mackExperiment0_0;
    else path = plateUrl;

    d3.json(path, function (error, json) {
        if (error) return console.warn(error);
        else {
             callback(json);
        }
    });
};