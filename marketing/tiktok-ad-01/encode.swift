// Baut aus einer JPEG-Bildfolge (f_00000.jpg ...) und einer WAV-Datei ein MP4 (H.264 + AAC).
// Aufruf: encode <frames-dir> <fps> <frame-count> <audio.wav> <out.mp4> [breite hoehe]
import AVFoundation
import CoreGraphics
import CoreVideo
import Foundation
import ImageIO

let args = CommandLine.arguments
guard args.count == 6 || args.count == 8, let fps = Int32(args[2]), let count = Int(args[3]) else {
    print("Aufruf: encode <frames-dir> <fps> <frame-count> <audio.wav> <out.mp4> [breite hoehe]")
    exit(2)
}
let dir = args[1]
let wavPath = args[4]
let outPath = args[5]
let width = args.count == 8 ? (Int(args[6]) ?? 1080) : 1080
let height = args.count == 8 ? (Int(args[7]) ?? 1920) : 1920

try? FileManager.default.removeItem(atPath: outPath)
let writer = try AVAssetWriter(outputURL: URL(fileURLWithPath: outPath), fileType: .mp4)

let videoSettings: [String: Any] = [
    AVVideoCodecKey: AVVideoCodecType.h264,
    AVVideoWidthKey: width,
    AVVideoHeightKey: height,
    AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: Int(ProcessInfo.processInfo.environment["VIDEO_BITRATE"] ?? "") ?? 10_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
        AVVideoMaxKeyFrameIntervalKey: Int(fps) * 2,
    ],
]
let vInput = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
vInput.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(
    assetWriterInput: vInput,
    sourcePixelBufferAttributes: [
        kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
        kCVPixelBufferWidthKey as String: width,
        kCVPixelBufferHeightKey as String: height,
    ])
writer.add(vInput)

let audioSettings: [String: Any] = [
    AVFormatIDKey: kAudioFormatMPEG4AAC,
    AVNumberOfChannelsKey: 2,
    AVSampleRateKey: 44100,
    AVEncoderBitRateKey: 160_000,
]
let aInput = AVAssetWriterInput(mediaType: .audio, outputSettings: audioSettings)
aInput.expectsMediaDataInRealTime = false
writer.add(aInput)

let asset = AVURLAsset(url: URL(fileURLWithPath: wavPath))
let reader = try AVAssetReader(asset: asset)
guard let track = asset.tracks(withMediaType: .audio).first else {
    print("Keine Audiospur in \(wavPath)")
    exit(3)
}
let readerOut = AVAssetReaderTrackOutput(track: track, outputSettings: [
    AVFormatIDKey: kAudioFormatLinearPCM,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
    AVLinearPCMIsBigEndianKey: false,
    AVLinearPCMIsNonInterleaved: false,
    AVSampleRateKey: 44100,
    AVNumberOfChannelsKey: 2,
])
reader.add(readerOut)

func pixelBuffer(_ path: String) -> CVPixelBuffer? {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { return nil }
    var pbOpt: CVPixelBuffer?
    let attrs: [String: Any] = [
        kCVPixelBufferCGImageCompatibilityKey as String: true,
        kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
    ]
    CVPixelBufferCreate(nil, width, height, kCVPixelFormatType_32BGRA, attrs as CFDictionary, &pbOpt)
    guard let pb = pbOpt else { return nil }
    CVPixelBufferLockBaseAddress(pb, [])
    defer { CVPixelBufferUnlockBaseAddress(pb, []) }
    guard let ctx = CGContext(
        data: CVPixelBufferGetBaseAddress(pb), width: width, height: height, bitsPerComponent: 8,
        bytesPerRow: CVPixelBufferGetBytesPerRow(pb), space: CGColorSpace(name: CGColorSpace.sRGB)!,
        bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)
    else { return nil }
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: width, height: height))
    return pb
}

reader.startReading()
writer.startWriting()
writer.startSession(atSourceTime: .zero)

let group = DispatchGroup()
let vQueue = DispatchQueue(label: "video")
let aQueue = DispatchQueue(label: "audio")
var frame = 0

group.enter()
vInput.requestMediaDataWhenReady(on: vQueue) {
    while vInput.isReadyForMoreMediaData {
        if frame >= count {
            vInput.markAsFinished()
            group.leave()
            return
        }
        let path = String(format: "%@/f_%05d.jpg", dir, frame)
        guard let pb = pixelBuffer(path) else {
            print("Frame fehlt: \(path)")
            exit(4)
        }
        adaptor.append(pb, withPresentationTime: CMTime(value: CMTimeValue(frame), timescale: fps))
        frame += 1
    }
}

group.enter()
aInput.requestMediaDataWhenReady(on: aQueue) {
    while aInput.isReadyForMoreMediaData {
        if let sb = readerOut.copyNextSampleBuffer() {
            aInput.append(sb)
        } else {
            aInput.markAsFinished()
            group.leave()
            return
        }
    }
}

group.wait()
let done = DispatchSemaphore(value: 0)
writer.finishWriting { done.signal() }
done.wait()
if writer.status == .completed {
    print("OK \(outPath)")
} else {
    print("Fehler: \(String(describing: writer.error))")
    exit(5)
}
