var classExperimentSelected = "ExperimentSelected";
var dispatcherSelectedExperiment = "SelectedExperiment";
var plateMetaDataType = {
    OK: "OK",
    BadData: "BadData",
    Empty: "Empty",
    NoGrowth: "NoGrowth",
    UndecidedProblem: "UndecidedProblem"
}

if (!d3.scanomatic) d3.scanomatic = {};


function executeFunctionByName(functionName, context /*, args */) {
    var args = Array.prototype.slice.call(arguments, 2);
    var namespaces = functionName.split(".");
    var func = namespaces.pop();
    for (var i = 0; i < namespaces.length; i++) {
        context = context[namespaces[i]];
    }
    return context[func].apply(context, args);
}

function DrawPlate(container, data, growthMetaData, plateMetaData) {

    //plate
    var cols = data[0].length;
    var rows = data.length;
    //experiment
    var circleRadius = 4;
    var circleMargin = 1;
    var cellSize = (circleRadius * 2) + circleMargin;
    //heatmap
    var heatmapMargin = 7;
    var scaleWidth = 30;
    var gridwidth = (cols * cellSize) + scaleWidth + (heatmapMargin * 2);
    var gridheight = (rows * cellSize) + (heatmapMargin * 2);
    var colorScheme = ["blue", "white", "red"];
    //heatmap legend
    var legendWidth = 25;
    var legendMargin = 5;
    
    //SetDebugText(data, cols, rows);

    var grid = d3.select(container)
        .append("svg")
        .attr({
            "width": gridwidth + legendMargin + legendWidth,
            "height": gridheight,
            "class": "PlateHeatMap"
        });

    addSymbolsToSGV(grid);
   
    var plateGroup = grid.append("g");

    //heatmap
    var heatMap = d3.scanomatic.plateHeatmap();
    heatMap.data(data);
    heatMap.growthMetaData(growthMetaData);
    heatMap.plateMetaData(plateMetaData);
    heatMap.cellSize(cellSize);
    heatMap.cellRadius(circleRadius);
    heatMap.setColorScale(colorScheme);
    heatMap.margin(heatmapMargin);
    heatMap.legendWidth(legendWidth);
    heatMap.legendMargin(legendMargin);
    heatMap.displayLegend(true);
    heatMap(plateGroup);
    //heatMap.on(dispatcherSelectedExperiment, function (datah) {
    //    console.log("dispatched:" + datah);
    //});
    return d3.rebind(DrawPlate, heatMap, "on");
};

function addSymbolsToSGV(svgRoot) {
    
    svgRoot.append("symbol")
       .attr({
           "id": "symEmpty",
           "viewBox": "0 0 24 30"
       })
       .append("path")
           .attr("d", "M22.707,1.293c-0.391-0.391-1.023-0.391-1.414,0L16.9,5.686C15.546,4.633,13.849,4,12,4c-4.418,0-8,3.582-8,8  c0,1.849,0.633,3.546,1.686,4.9l-4.393,4.393c-0.391,0.391-0.391,1.023,0,1.414C1.488,22.902,1.744,23,2,23s0.512-0.098,0.707-0.293  L7.1,18.314C8.455,19.367,10.151,20,12,20c4.418,0,8-3.582,8-8c0-1.849-0.633-3.545-1.686-4.9l4.393-4.393  C23.098,2.316,23.098,1.684,22.707,1.293z M6,12c0-3.309,2.691-6,6-6c1.294,0,2.49,0.416,3.471,1.115l-8.356,8.356  C6.416,14.49,6,13.294,6,12z M18,12c0,3.309-2.691,6-6,6c-1.294,0-2.49-0.416-3.471-1.115l8.356-8.356C17.584,9.51,18,10.706,18,12z");

    svgRoot.append("symbol")
        .attr({
            "id": "symUndecided",
            "viewBox": "0 0 100 100"
        })
        .append("path")
            .attr("d", "M50.1,5c-13,0-23.7,10.7-23.7,23.7c0,3.9,3.3,7.2,7.3,7.2c4.1,0,7.3-3.3,7.3-7.2c0-5,4.1-9.1,9.1-9.1c4.9,0,8.9,4.1,8.9,9.1  c0,4.6-2,6.9-5.7,11.1c-4.6,4.7-10.7,11.2-10.7,23.6c0,4.2,3.3,7.4,7.4,7.4c4,0,7.2-3.2,7.2-7.4c0-6.7,2.8-9.7,6.6-13.7  c4.3-4.7,9.6-10.4,9.6-21.1C73.6,15.7,63.1,5,50.1,5L50.1,5z M50.1,77.4c-4.9,0-8.9,3.8-8.9,8.8c0,4.9,4,8.8,8.9,8.8  c4.7,0,8.8-3.9,8.8-8.8C58.9,81.3,54.9,77.4,50.1,77.4z");

    var badDataSym = svgRoot.append("symbol")
        .attr({
            "id": "symBadData",
            "viewBox": "0 0 100 125"
        });
    badDataSym.append("path")
        .attr("d", "M94.202,80.799L55.171,13.226c-1.067-1.843-3.022-2.968-5.147-2.968c-0.008,0-0.016,0-0.023,0s-0.016,0-0.023,0  c-2.124,0-4.079,1.125-5.147,2.968L5.798,80.799c-1.063,1.85-1.063,4.124,0,5.969c1.057,1.846,3.024,2.976,5.171,2.976h78.063  c2.146,0,4.114-1.13,5.171-2.976C95.266,84.923,95.266,82.646,94.202,80.799z M14.412,81.79L50,20.182L85.588,81.79H14.412z")
    badDataSym.append("polygon")
        .attr("points", "64.512,70.413 56.414,62.164 64.305,54.188 57.873,47.826 50.075,55.709 42.212,47.7 35.757,54.038 43.713,62.141 35.489,70.455 41.92,76.817 50.051,68.598 58.057,76.751");

    svgRoot.append("symbol")
        .attr({
            "id": "symNoGrowth",
            "viewBox": "0 0 100 125"
        })
        .append("path")
            .attr("d", "M50,95c24.853,0,45-20.147,45-45C95,25.147,74.853,5,50,5S5,25.147,5,50C5,74.853,25.147,95,50,95z M25,45h50v10H25V45z");
}

function SetDebugText(data, cols, rows) {

    d3.select("#text").append("p").text("cols = " + cols);
    d3.select("#text").append("p").text("rows = " + rows);

    var min = d3.min(data[0]);
    var max = d3.max(data[0]);
    var mean = d3.mean(data[0]);
    d3.select("#text").append("p").text("min = " + min);
    d3.select("#text").append("p").text("max = " + max);
    d3.select("#text").append("p").text("mean = " + mean);
}

d3.scanomatic.plateHeatmap = function () {

    //properties
    var data;
    var growthMetaData;
    var plateMetaData;
    var cellSize;
    var cellRadius;
    var colorScale;
    var colorSchema;
    var margin;
    var displayLegend;
    var legendMargin;
    var legendWidth;

    // local variables
    var g;
    var cols;
    var rows;
    var phenotypeMin;
    var phenotypeMax;
    var phenotypeMean;
    

    var dispatch = d3.dispatch(dispatcherSelectedExperiment);
    
    function heatmap(container) {
        g = container;
        g.append("g").classed("heatmap", true);
        update();
    }

    heatmap.update = update;
    function update() {

        //compose from plate metadata
        var plateMetaDataComp = [];
        plateMetaDataComp.push(addmetaDataType(plateMetaData.plate_BadData, plateMetaDataType.BadData));
        plateMetaDataComp.push(addmetaDataType(plateMetaData.plate_Empty, plateMetaDataType.Empty));
        plateMetaDataComp.push(addmetaDataType(plateMetaData.plate_NoGrowth, plateMetaDataType.NoGrowth));
        plateMetaDataComp.push(addmetaDataType(plateMetaData.plate_UndecidedProblem, plateMetaDataType.UndecidedProblem));

        //compose from plate data and growth metadata
        var plateData = [];
        for (var i = 0; i < rows; i++) {
            var row = [];
            for (var j = 0; j < cols; j++) {
                var metaData = findPlateMetaData(i, j, plateMetaDataComp);
                var col = { phenotype: data[i][j], metaGT: growthMetaData.gt[i][j], metaGtWhen: growthMetaData.gtWhen[i][j], metaYield: growthMetaData.yld[i][j], metaType: metaData.type }
                row.push(col);
            }
            plateData.push(row);
        }

        var div = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);

        var gHeatMap = g.selectAll(".rows")
        .data(plateData)
        .enter().append("g")
        .attr({
            "transform": function (d, i) { var x = 0 + margin; var y = (i * cellSize) + margin; return "translate(" + x + "," + y + ")"; },
            "data-row": function (d, i) { return i }
        });

        var nodes = gHeatMap.selectAll("nodes")
            .data(function(d) { return d; })
            .enter()
            .append("g")
            .attr("class", "expNode")
            .on("mouseover", function () { onMouseOver(d3.select(this)) })
            .on("mouseout", function () { onMouseOut(d3.select(this)) })
            .on("click", function (element) { onClick(d3.select(this.parentNode), d3.select(this), element) });

        nodes.append("circle")
            .attr({
                "class": "plateWell",
                "fill": function(d) {
                    return getValidColor(d.phenotype);
                },
                "id": function(d, i) {
                    var row = d3.select(this.parentNode).attr("data-row");
                    var col = i;
                    return row + "/" + col;
                },
                "fill-opacity": "1",
                "r": cellRadius,
                "cy": cellRadius,
                "cx": function(d, i) { return cellRadius + i * cellSize; },
                "data-col": function (d, i) { return i; },
                "data-meta-gt": function (d) { return d.metaGT; },
                "data-meta-gtWhen": function (d) { return d.metaGtWhen; },
                "data-meta-yield": function (d) { return d.metaYield; },
                "data-meta-type": function (d) { return d.metaType; }
                //"visibility": function(d) {
                //    if (d.metaType != plateMetaDataType.OK) return "hidden";
                //    return "visible";
                //}
            });

        nodes
            .append("use")
            .filter(function(d) { return d.metaType == plateMetaDataType.Empty; })
            .attr({
                "class": "plateWellSymbol",
                "xlink:href": "#symEmpty",
                "x": function(d, i) { return (i * cellSize) - 2; },
                "y": 0 -.8,
                "width": cellRadius * 3,
                "height": cellRadius * 3
            });

        nodes
            .append("use")
            .filter(function (d) { return d.metaType == plateMetaDataType.UndecidedProblem; })
            .attr({
                "class": "plateWellSymbol",
                "xlink:href": "#symUndecided",
                "x": function (d, i) { return (i * cellSize) - 2; },
                "y": 0 ,
                "width": cellRadius * 3,
                "height": cellRadius * 2
            });

        nodes
            .append("use")
            .filter(function (d) { return d.metaType == plateMetaDataType.BadData; })
            .attr({
                "class": "plateWellSymbol",
                "xlink:href": "#symBadData",
                "x": function (d, i) { return (i * cellSize) - 2; },
                "y": 0,
                "width": cellRadius * 3,
                "height": cellRadius * 2
            });

        nodes
            .append("use")
            .filter(function (d) { return d.metaType == plateMetaDataType.NoGrowth; })
            .attr({
                "class": "plateWellSymbol",
                "xlink:href": "#symNoGrowth",
                "x": function (d, i) { return (i * cellSize) - 1; },
                "y": 0,
                "width": cellRadius * 2.5,
                "height": cellRadius * 2.5
            });

        //symNoGrowth

        if (displayLegend) {
            createLegend(g);
        }

        function onClick(rowNode, thisNode, element) {
            var row = rowNode.attr("data-row");
            var well = thisNode.select(".plateWell");
            var col = well.attr("data-col");
            var metaDataGt = well.attr("data-meta-gt");
            var metaDataGtWhen = well.attr("data-meta-gtWhen");
            var metaDataYield = well.attr("data-meta-yield");
            var coord = row + "," + col;
            var coordinate = "[" + coord + "]";
            var exp = { coord: coord, metaDataGt: metaDataGt, metaDataGtWhen: metaDataGtWhen, metaDataYield: metaDataYield };
            //deselect preavius selections
            var sel = g.selectAll("." + classExperimentSelected);
            sel.classed(classExperimentSelected, false);
            sel.attr({"stroke-width": 0});
            //new selection
            var newSel = well;
            newSel.classed(classExperimentSelected, true);
            newSel.attr({
                "stroke": "black",
                "stroke-width" :3
            });
            //phenotype:
            var pheno = element;
            d3.select("#sel").selectAll("*").remove();
            d3.select("#sel").append("p").text("Experiment " + coordinate);
            //d3.select("#sel").append("span").text("GT " + metaDataGt);
            //d3.select("#sel").append("span").text("GTWhen " + metaDataGtWhen);
            //d3.select("#sel").append("span").text("Yield " + metaDataYield);
            //d3.select("#sel").append("p").text("Phenotype = " + pheno);
            dispatch[dispatcherSelectedExperiment](exp);
        }

        function onMouseOut(node) {
            node.select(".plateWell").attr("fill", function (d) { return getValidColor(d.phenotype); });
            node.select(".plateWellSymbol").attr("fill", "black");

            div.transition()
                .duration(0)
                .style("opacity", 0);
        }

        function onMouseOver(node) {

            var fmt = d3.format("0.3s");
            div.transition()
                    .duration(0)
                    .style("opacity", .9);

            node.select(".plateWellSymbol")
                .attr("fill", "white");

            node.select(".plateWell")
                .attr("fill", "black").attr("", function(d) {
                    div.html(fmt(d.phenotype))
                        .style("left", (d3.event.pageX) + "px")
                        .style("top", (d3.event.pageY - 20) + "px");
                });
        }

        function findPlateMetaData(row, col, metaData) {
            for (var typeI = 0; typeI < metaData.length; typeI++) {
                var type = metaData[typeI];
                for (var itemI = 0; itemI < type.length; itemI++) {
                    var item = type[itemI];
                    if (item.row == row && item.col == col)
                        return item;
                }
            }
            return { row: row, col: col, type: plateMetaDataType.OK };
        }

        function addmetaDataType(metaDataType, typeName) {
            var dataType = [];
            var badDataElement;
            for (var k = 0; k < metaDataType[0].length; k++) {
                badDataElement = { row: metaDataType[0][k], col: metaDataType[1][k], type: typeName };
                dataType.push(badDataElement);
            }
            return dataType;
        }
    }

    function getValidColor(d) {
        var color;
        if (d !== null)
            color = colorScale(d);
        else
            color = "white";
        return color;
    }

    function createLegend(container) {

        var startX = margin + (cols * cellSize) + legendMargin;
        var startY = margin;
        var heatMaphight = (rows * cellSize) ;
        var gLegendScale = container.append("g");

        var gradient = gLegendScale
            .append("linearGradient")
            .attr({
                "y1": "0%",
                "y2": "100%",
                "x1": "0",
                "x2": "0",
                "id": "gradient"
            });

        gradient
            .append("stop")
            .attr({
                "offset": "0%",
                "stop-color": colorSchema[2]
            });

        gradient
            .append("stop")
            .attr({
                "offset": "50%",
                "stop-color": colorSchema[1]
            });

        gradient
            .append("stop")
                .attr({
                    "offset": "100%",
                    "stop-color": colorSchema[0]
                });

        gLegendScale.append("rect")
            .attr({
                y: startY,
                x: startX,
                width: legendWidth,
                height: heatMaphight
            }).style({
                fill: "url(#gradient)",
                "stroke-width": 2,
                "stroke": "black"
            });

        var gLegendaxis = container.append("g").classed("HeatMapLegendAxis",true);

        var legendScale = d3.scale.linear()
        .domain( d3.extent(data[0]).reverse())
        .rangeRound([startY, heatMaphight])
        .nice();

        var gradAxis = d3.svg.axis()
            .scale(legendScale)
            .orient("right")
            .tickSize(10)
            .ticks(10)
            .tickFormat(d3.format("0.3s"));

        gradAxis(gLegendaxis);
        gLegendaxis.attr({
            "transform": "translate(" + (startX + legendWidth-9) + ", " + (margin/2) + ")"
        });
        gLegendaxis.selectAll("path").style({ fill: "none", stroke: "#000" });
        gLegendaxis.selectAll("line").style({ stroke: "#000" });
    }

    heatmap.data = function(value) {
        if (!arguments.length) return data;
        data = value;
        cols = data[0].length;
        rows = data.length;
        phenotypeMin = d3.min(data[0]);
        phenotypeMax = d3.max(data[0]);
        phenotypeMean = d3.mean(data[0]);
        return heatmap;
    }

    heatmap.growthMetaData = function (value) {
        if (!arguments.length) return growthMetaData;
        growthMetaData = value;
        return heatmap;
    }

    heatmap.plateMetaData = function (value) {
        if (!arguments.length) return plateMetaData;
        plateMetaData = value;
        return heatmap;
    }

    heatmap.cellSize = function(value) {
        if (!arguments.length) return cellSize;
        cellSize = value;
        return heatmap;
    }

    heatmap.cellRadius = function(value) {
        if (!arguments.length) return cellRadius;
        cellRadius = value;
        return heatmap;
    }

    heatmap.colorScale = function(value) {
        if (!arguments.length) return colorScale;
        colorScale = value;
        return heatmap;
    }

    heatmap.colorSchema = function (value) {
        if (!arguments.length) return colorSchema;
        colorSchema = value;
        return heatmap;
    }

    heatmap.setColorScale = function(value) {
        
        if (typeof value === "undefined" || value === null) {
            throw "colorSchema isundefined";
        }
        if (typeof data === "undefined" || data === null) {
            throw "data is not set!";
        }

        colorSchema = value;
        var cs = d3.scale.linear()
            .domain([phenotypeMin, phenotypeMean, phenotypeMax])
            .range([colorSchema[0], colorSchema[1], colorSchema[2]]);
        colorScale = cs;
    }

    heatmap.margin = function (value) {
        if (!arguments.length) return margin;
        margin = value;
        return heatmap;
    }

    heatmap.displayLegend = function (value) {
        if (!arguments.length) return displayLegend;
        displayLegend = value;
        return heatmap;
    }

    heatmap.legendMargin = function (value) {
        if (!arguments.length) return legendMargin;
        legendMargin = value;
        return heatmap;
    }

    heatmap.legendWidth = function (value) {
        if (!arguments.length) return legendWidth;
        legendWidth = value;
        return heatmap;
    }
    
    return d3.rebind(heatmap, dispatch, "on");
}


