-- ExportModule.lua
-- File export API wrapper for Lightroom Classic.

local LrApplication = nil
local LrExportSession = nil
local LrFileUtils = nil
local LrPathUtils = nil
local LrTasks = import 'LrTasks'

local function getErrorUtils()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.ErrorUtils then
        return _G.LightroomPythonBridge.ErrorUtils
    end
    return {
        safeCall = function(func, ...) return LrTasks.pcall(func, ...) end,
        createError = function(code, message) return { error = { code = code or "ERROR", message = message or "An error occurred", severity = "error" } } end,
        createSuccess = function(result) return { result = result or {} } end,
    }
end

local ErrorUtils = getErrorUtils()

local function ensureLrModules()
    if not LrApplication then
        LrApplication = import 'LrApplication'
    end
    if not LrExportSession then
        LrExportSession = import 'LrExportSession'
    end
    if not LrFileUtils then
        LrFileUtils = import 'LrFileUtils'
    end
    if not LrPathUtils then
        LrPathUtils = import 'LrPathUtils'
    end
end

local function getLogger()
    if _G.LightroomPythonBridge and _G.LightroomPythonBridge.logger then
        return _G.LightroomPythonBridge.logger
    end
    local LrLogger = import 'LrLogger'
    local logger = LrLogger('ExportModule')
    logger:enable("logfile")
    return logger
end

local ExportModule = {}

local function normalizeFormat(format)
    format = string.upper(tostring(format or "JPEG"))
    if format == "JPG" then
        return "JPEG"
    end
    return format
end

local function buildExportSettings(params)
    local outputDir = params.outputDir
    local format = normalizeFormat(params.format)
    local quality = tonumber(params.quality or 95)
    local colorSpace = params.colorSpace or "sRGB"
    local overwrite = params.overwrite == true

    local settings = {
        LR_export_destinationType = "specificFolder",
        LR_export_destinationPathPrefix = outputDir,
        LR_export_useSubfolder = false,
        LR_collisionHandling = overwrite and "overwrite" or "rename",
        LR_format = format,
    }

    if format == "JPEG" then
        settings.LR_jpeg_quality = quality / 100
        settings.LR_export_colorSpace = colorSpace
    elseif format == "TIFF" then
        settings.LR_tiff_compressionMethod = "compressionMethod_None"
        settings.LR_export_colorSpace = colorSpace
    end

    if params.resizeLongEdge then
        local longEdge = tonumber(params.resizeLongEdge)
        settings.LR_size_doConstrain = true
        settings.LR_size_resizeType = "longEdge"
        settings.LR_size_maxHeight = longEdge
        settings.LR_size_maxWidth = longEdge
        settings.LR_size_units = "pixels"
    end

    return settings
end

local function findPhotosByIds(photoIds)
    local catalog = LrApplication.activeCatalog()
    local photos = {}
    local missing = {}

    catalog:withReadAccessDo(function()
        for _, photoId in ipairs(photoIds) do
            local photo = catalog:getPhotoByLocalId(tonumber(photoId))
            if photo then
                table.insert(photos, photo)
            else
                table.insert(missing, tostring(photoId))
            end
        end
    end)

    return photos, missing
end

local function pathWithSuffix(path, suffix)
    if not suffix or suffix == "" then
        return path
    end

    local leaf = LrPathUtils.leafName(path)
    local parent = LrPathUtils.parent(path)
    local extension = string.match(leaf, "(%.[^%.]+)$") or ""
    local stem = leaf
    if extension ~= "" then
        stem = string.sub(leaf, 1, string.len(leaf) - string.len(extension))
    end
    return LrPathUtils.child(parent, stem .. suffix .. extension)
end

local function moveWithSuffix(path, suffix, overwrite)
    local destination = pathWithSuffix(path, suffix)
    if destination == path then
        return path
    end

    if overwrite and LrFileUtils.exists(destination) then
        LrFileUtils.delete(destination)
    end

    local moved = LrFileUtils.move(path, destination)
    if moved then
        return destination
    end
    return path
end

local function exportRenditions(photos, params)
    local exportSettings = buildExportSettings(params)
    local session = LrExportSession({
        photosToExport = photos,
        exportSettings = exportSettings,
    })

    local results = {}
    local files = {}
    local exported = 0
    local failed = 0

    for _, rendition in session:renditions({ stopIfCanceled = true }) do
        local success, pathOrMessage = rendition:waitForRender()
        if success then
            local outputPath = moveWithSuffix(pathOrMessage, params.filenameSuffix, params.overwrite == true)
            table.insert(files, outputPath)
            table.insert(results, {
                success = true,
                path = outputPath,
            })
            exported = exported + 1
        else
            table.insert(results, {
                success = false,
                error = tostring(pathOrMessage),
            })
            failed = failed + 1
        end
    end

    return {
        exported = exported,
        failed = failed,
        files = files,
        results = results,
        outputDir = params.outputDir,
        format = normalizeFormat(params.format),
    }
end

local function runExport(photoIds, params, callback)
    ensureLrModules()
    local logger = getLogger()

    if not params.outputDir or params.outputDir == "" then
        callback(ErrorUtils.createError("MISSING_OUTPUT_DIR", "outputDir is required"))
        return
    end

    LrTasks.startAsyncTask(function()
        local success, result = ErrorUtils.safeCall(function()
            logger:info("Exporting " .. tostring(#photoIds) .. " photo(s) to " .. tostring(params.outputDir))
            LrFileUtils.createAllDirectories(params.outputDir)

            local photos, missing = findPhotosByIds(photoIds)
            if #missing > 0 then
                return {
                    error = {
                        code = "PHOTO_NOT_FOUND",
                        message = "Photo ID(s) not found: " .. table.concat(missing, ", "),
                    }
                }
            end
            if #photos == 0 then
                return {
                    error = {
                        code = "NO_PHOTOS",
                        message = "No photos to export",
                    }
                }
            end

            return exportRenditions(photos, params)
        end)

        if not success then
            callback(ErrorUtils.createError("EXPORT_FAILED", "Failed to export photos: " .. tostring(result)))
        elseif result and result.error then
            callback({ error = result.error })
        else
            callback({
                success = true,
                result = result,
            })
        end
    end)
end

function ExportModule.exportPhoto(params, callback)
    params = params or {}
    if not params.photoId or params.photoId == "" then
        callback(ErrorUtils.createError("MISSING_PHOTO_ID", "photoId is required"))
        return
    end
    runExport({ params.photoId }, params, callback)
end

function ExportModule.exportBatch(params, callback)
    params = params or {}
    if type(params.photoIds) ~= "table" or #params.photoIds == 0 then
        callback(ErrorUtils.createError("MISSING_PHOTO_IDS", "photoIds array is required"))
        return
    end
    runExport(params.photoIds, params, callback)
end

return ExportModule
